"""Benchmark evaluation against externally labelled retrieval datasets.

This module intentionally keeps benchmark state separate from the live demo
index.  It reads the BEIR corpus/query/qrels format, builds an ephemeral
GroundDesk-compatible index, and evaluates ranked document retrieval.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np

from app.core.config import Settings
from app.rag.ingestion.chunking import chunk_text
from app.rag.ingestion.quality import filter_chunks
from app.rag.retrieval.embeddings import EmbeddingModel
from app.rag.retrieval.retriever import HybridRetriever
from app.rag.retrieval.vector_store import (
    ChunkRecord,
    DocumentManifest,
    LocalVectorStore,
)


@dataclass(frozen=True)
class BenchmarkDocument:
    document_id: str
    title: str
    text: str


@dataclass(frozen=True)
class BenchmarkDataset:
    name: str
    documents: dict[str, BenchmarkDocument]
    queries: dict[str, str]
    qrels: dict[str, dict[str, int]]
    split: str
    selection: dict | None = None

    @property
    def evaluated_query_ids(self) -> list[str]:
        return sorted(query_id for query_id in self.qrels if query_id in self.queries)


@dataclass(frozen=True)
class BenchmarkIndexStats:
    documents: int
    chunks: int
    embedding_backend: str
    embedding_model: str
    vector_dimensions: dict[str, int]
    vector_footprint_bytes: int
    build_seconds: float
    request_delay_seconds: float = 0.0


def load_beir_dataset(dataset_dir: Path, *, split: str = "test") -> BenchmarkDataset:
    """Load a BEIR-format dataset from ``corpus.jsonl``, ``queries.jsonl`` and qrels."""
    corpus_path = dataset_dir / "corpus.jsonl"
    queries_path = dataset_dir / "queries.jsonl"
    qrels_path = dataset_dir / "qrels" / f"{split}.tsv"
    required = (corpus_path, queries_path, qrels_path)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing BEIR dataset files: "
            + ", ".join(missing)
            + ". Download or extract the dataset before running the benchmark."
        )

    documents: dict[str, BenchmarkDocument] = {}
    for payload in _read_jsonl(corpus_path):
        document_id = str(payload["_id"])
        documents[document_id] = BenchmarkDocument(
            document_id=document_id,
            title=str(payload.get("title") or document_id),
            text=str(payload.get("text") or ""),
        )

    queries = {
        str(payload["_id"]): str(payload.get("text") or "")
        for payload in _read_jsonl(queries_path)
    }
    qrels = _read_qrels(qrels_path)
    return BenchmarkDataset(
        name=dataset_dir.name,
        documents=documents,
        queries=queries,
        qrels=qrels,
        split=split,
    )


def select_labelled_slice(
    dataset: BenchmarkDataset,
    *,
    query_count: int,
    corpus_document_count: int,
    seed: int,
) -> BenchmarkDataset:
    """Create a reproducible API-budget-controlled slice.

    All positive qrel documents for selected queries are retained; random
    distractors are then added. This is an integration/evaluation slice, not a
    substitute for a full-corpus public benchmark.
    """
    if query_count < 1:
        raise ValueError("query_count must be positive.")
    query_ids = dataset.evaluated_query_ids
    if query_count > len(query_ids):
        raise ValueError("query_count exceeds the labelled query count.")
    generator = random.Random(seed)
    selected_query_ids = sorted(generator.sample(query_ids, query_count))
    relevant_document_ids = {
        document_id
        for query_id in selected_query_ids
        for document_id, grade in dataset.qrels[query_id].items()
        if grade > 0
    }
    if len(relevant_document_ids) > corpus_document_count:
        raise ValueError(
            f"Selected qrels require {len(relevant_document_ids)} positive documents, "
            f"which exceeds corpus_document_count={corpus_document_count}."
        )
    distractors = sorted(set(dataset.documents) - relevant_document_ids)
    sampled_distractors = generator.sample(
        distractors,
        min(corpus_document_count - len(relevant_document_ids), len(distractors)),
    )
    selected_document_ids = relevant_document_ids | set(sampled_distractors)
    return BenchmarkDataset(
        name=f"{dataset.name}_gemini_slice",
        documents={
            document_id: dataset.documents[document_id]
            for document_id in sorted(selected_document_ids)
        },
        queries={
            query_id: dataset.queries[query_id] for query_id in selected_query_ids
        },
        qrels={query_id: dataset.qrels[query_id] for query_id in selected_query_ids},
        split=dataset.split,
        selection={
            "source_dataset": dataset.name,
            "method": "random labelled queries; all positive qrel documents retained; random distractors added",
            "seed": seed,
            "selected_queries": query_count,
            "selected_documents": len(selected_document_ids),
            "positive_documents": len(relevant_document_ids),
            "not_full_benchmark": True,
        },
    )


def build_benchmark_index(
    dataset: BenchmarkDataset,
    embeddings: EmbeddingModel,
    *,
    index_dir: Path,
    embedding_batch_size: int = 64,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[LocalVectorStore, BenchmarkIndexStats]:
    """Create an isolated index without mutating live application data.

    The index uses GroundDesk's chunk records, chunk quality threshold,
    embeddings and local vector search semantics.  It writes once after bulk
    construction rather than invoking the interactive ingestion save path for
    thousands of benchmark documents.
    """
    started = perf_counter()
    store = LocalVectorStore(index_dir)
    store.documents = {}
    store.records = []
    store.vectors = {}
    store.index_metadata = {}

    records: list[ChunkRecord] = []
    manifests: dict[str, DocumentManifest] = {}
    now = datetime.now(UTC).isoformat()
    for document in dataset.documents.values():
        text = document.text.strip() or document.title
        candidate_chunks = chunk_text(text, document.document_id)
        chunks, warnings = filter_chunks(candidate_chunks)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        version_id = f"benchmark_{content_hash[:12]}"
        document_records = [
            ChunkRecord(
                chunk_id=chunk.chunk_id,
                document_id=document.document_id,
                version_id=version_id,
                title=document.title,
                source_type="benchmark",
                source=f"beir:{dataset.name}",
                text=chunk.text,
                position=chunk.position,
                section_title=chunk.section_title,
                section_path=chunk.section_path,
                page_number=chunk.page_number,
                word_count=chunk.word_count,
                content_hash=chunk.content_hash,
            )
            for chunk in chunks
        ]
        records.extend(document_records)
        manifests[document.document_id] = DocumentManifest(
            document_id=document.document_id,
            source_id=f"beir:{dataset.name}:{document.document_id}",
            version_id=version_id,
            content_hash=content_hash,
            title=document.title,
            source_type="benchmark",
            source=f"beir:{dataset.name}",
            original_filename=None,
            chunks_indexed=len(document_records),
            ingested_at=now,
            status="indexed" if document_records else "rejected",
            warnings=tuple(warnings),
            metadata={"benchmark_dataset": dataset.name},
        )

    if not records:
        raise ValueError("The benchmark corpus produced no retrievable chunks.")

    vector_blocks: dict[str, list[np.ndarray]] = defaultdict(list)
    for start in range(0, len(records), embedding_batch_size):
        batch_records = records[start : start + embedding_batch_size]
        batch = embeddings.encode_documents(
            [record.text for record in batch_records],
            titles=[record.title for record in batch_records],
        )
        if not store.index_metadata:
            store.register_embedding_space(
                model_name=embeddings.model_name,
                backend=embeddings.backend,
                dimensions=batch.dimensions,
                default_vector_name=batch.default_name,
            )
        for name, matrix in batch.vectors.items():
            vector_blocks[name].append(matrix)
        if progress_callback is not None:
            progress_callback(
                min(start + len(batch_records), len(records)), len(records)
            )

    store.records = records
    store.documents = manifests
    store.vectors = {
        name: np.vstack(blocks).astype(np.float32)
        for name, blocks in vector_blocks.items()
    }
    # Persist a single isolated benchmark index for reproducibility and inspection.
    store.save()
    vector_bytes = sum(matrix.nbytes for matrix in store.vectors.values())
    return store, BenchmarkIndexStats(
        documents=len(manifests),
        chunks=len(records),
        embedding_backend=embeddings.backend,
        embedding_model=embeddings.model_name,
        vector_dimensions=store.vector_dimensions,
        vector_footprint_bytes=vector_bytes,
        build_seconds=perf_counter() - started,
        request_delay_seconds=embeddings.request_delay_seconds,
    )


def evaluate_retrieval_strategy(
    dataset: BenchmarkDataset,
    *,
    retriever: HybridRetriever,
    embeddings: EmbeddingModel,
    strategy: str,
    cutoffs: tuple[int, ...] = (1, 3, 5, 10),
    query_limit: int | None = None,
) -> dict:
    """Evaluate one retrieval policy against qrels at document level.

    GroundDesk returns chunks to generation.  For BEIR qrels, returned chunks
    are collapsed to their source document IDs before ranking is scored.
    """
    cutoffs = tuple(sorted(set(cutoffs)))
    max_k = max(cutoffs)
    query_ids = dataset.evaluated_query_ids
    if query_limit is not None:
        query_ids = query_ids[:query_limit]
    if not query_ids:
        raise ValueError("No labelled queries are available for evaluation.")

    recalls: dict[int, list[float]] = {k: [] for k in cutoffs}
    successes: dict[int, list[float]] = {k: [] for k in cutoffs}
    reciprocal_ranks: list[float] = []
    ndcg_values: list[float] = []
    ap_values: list[float] = []
    latencies_ms: list[float] = []
    failures: list[dict] = []

    for query_id in query_ids:
        query = dataset.queries[query_id]
        relevant = {
            document_id: grade
            for document_id, grade in dataset.qrels[query_id].items()
            if grade > 0
        }
        started = perf_counter()
        query_vectors = embeddings.encode_queries([query]).vectors
        ranked_chunks = retriever.retrieve(query, query_vectors, top_k=max_k)
        latencies_ms.append((perf_counter() - started) * 1000)
        ranked_document_ids = _distinct_document_ids(ranked_chunks)
        relevance = [
            relevant.get(document_id, 0) for document_id in ranked_document_ids
        ]

        for k in cutoffs:
            found = sum(
                1 for document_id in ranked_document_ids[:k] if document_id in relevant
            )
            recalls[k].append(found / len(relevant) if relevant else 0.0)
            successes[k].append(1.0 if found else 0.0)
        first_relevant_rank = next(
            (
                rank
                for rank, document_id in enumerate(ranked_document_ids[:max_k], start=1)
                if document_id in relevant
            ),
            None,
        )
        reciprocal_ranks.append(1 / first_relevant_rank if first_relevant_rank else 0.0)
        ndcg_values.append(_ndcg_at_k(relevance, list(relevant.values()), max_k))
        ap_values.append(_average_precision_at_k(ranked_document_ids, relevant, max_k))
        if first_relevant_rank is None:
            failures.append(
                {
                    "query_id": query_id,
                    "question": query,
                    "relevant_document_ids": sorted(relevant),
                    "ranked_document_ids": ranked_document_ids[:max_k],
                }
            )

    total = len(query_ids)
    metrics = {
        **{f"recall@{k}": _mean(recalls[k]) for k in cutoffs},
        **{f"success@{k}": _mean(successes[k]) for k in cutoffs},
        f"mrr@{max_k}": _mean(reciprocal_ranks),
        f"ndcg@{max_k}": _mean(ndcg_values),
        f"map@{max_k}": _mean(ap_values),
        f"no_hit_rate@{max_k}": len(failures) / total,
        "latency_p50_ms": _percentile(latencies_ms, 50),
        "latency_p95_ms": _percentile(latencies_ms, 95),
    }
    return {
        "strategy": strategy,
        "num_queries": total,
        "metrics": metrics,
        "failures": failures,
    }


def make_retriever(
    *,
    mode: str,
    store: LocalVectorStore,
    embeddings: EmbeddingModel,
    final_reranker: str = "lexical",
) -> HybridRetriever:
    settings = Settings(
        retrieval_mode=mode,
        adaptive_retrieval_enabled=mode == "adaptive",
        final_reranker=final_reranker,
        vector_store_backend="local",
    )
    return HybridRetriever(settings, store, embeddings=embeddings)


def build_benchmark_report(
    dataset: BenchmarkDataset,
    index_stats: BenchmarkIndexStats,
    runs: list[dict],
    *,
    query_limit: int | None = None,
) -> dict:
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "name": dataset.name,
            "split": dataset.split,
            "documents": len(dataset.documents),
            "labelled_queries": len(dataset.evaluated_query_ids),
            "evaluated_queries": runs[0]["num_queries"] if runs else 0,
            "query_limit": query_limit,
            "qrels_evaluation_unit": "top-k retrieved chunks collapsed to source documents",
            "selection": dataset.selection,
        },
        "index": asdict(index_stats),
        "runs": runs,
    }


def report_as_markdown(report: dict) -> str:
    dataset = report["dataset"]
    index = report["index"]
    lines = [
        "# GroundDesk Retrieval Benchmark Report",
        "",
        f"- **Dataset:** {dataset['name']} ({dataset['split']} split)",
        f"- **Corpus documents:** {dataset['documents']:,}",
        f"- **Evaluated labelled queries:** {dataset['evaluated_queries']:,} / {dataset['labelled_queries']:,}",
        f"- **Indexed chunks:** {index['chunks']:,}",
        f"- **Embeddings:** `{index['embedding_model']}` (`{index['embedding_backend']}`)",
        f"- **Index build time:** {index['build_seconds']:.2f}s",
        f"- **Vector footprint:** {index['vector_footprint_bytes'] / (1024 * 1024):.2f} MiB",
        "",
        "## Retrieval Performance",
        "",
        "| Strategy | Recall@5 | Success@5 | MRR@10 | nDCG@10 | MAP@10 | No hit@10 | p50 ms | p95 ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in report["runs"]:
        metrics = run["metrics"]
        lines.append(
            "| {strategy} | {recall:.3f} | {success:.3f} | {mrr:.3f} | "
            "{ndcg:.3f} | {map_value:.3f} | {no_hit:.3f} | {p50:.1f} | {p95:.1f} |".format(
                strategy=run["strategy"],
                recall=metrics.get("recall@5", 0.0),
                success=metrics.get("success@5", 0.0),
                mrr=metrics.get("mrr@10", 0.0),
                ndcg=metrics.get("ndcg@10", 0.0),
                map_value=metrics.get("map@10", 0.0),
                no_hit=metrics.get("no_hit_rate@10", 0.0),
                p50=metrics["latency_p50_ms"],
                p95=metrics["latency_p95_ms"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This report measures retrieval ranking against dataset relevance labels; it does not prove generated answer faithfulness.",
            "- Scores are document-level: retrieved chunks are mapped back to their source document IDs before comparison with qrels.",
            "- Latency is measured on the benchmark runner machine; it is not a hosted-service latency guarantee.",
            "- If a query limit was used, the report is a development run, not a full benchmark result.",
            "",
        ]
    )
    if dataset.get("selection"):
        selection = dataset["selection"]
        lines[2:2] = [
            "> **Controlled Gemini slice:** This is not a full public benchmark result. "
            "It validates the configured API embedding path on a reproducibly sampled labelled subset.",
            "",
        ]
        lines.insert(
            9,
            f"- **Sampling:** {selection['selected_queries']} labelled queries, "
            f"{selection['selected_documents']} documents, seed `{selection['seed']}`",
        )
    if index.get("request_delay_seconds", 0):
        lines.insert(
            -1,
            f"- API latency includes a `{index['request_delay_seconds']:.2f}s` per-request "
            "delay intentionally applied to protect free-tier quota.",
        )
    return "\n".join(lines)


def _read_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _read_qrels(path: Path) -> dict[str, dict[str, int]]:
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if index == 0 and fields[0].lower() in {"query-id", "query_id"}:
                continue
            if len(fields) < 3:
                raise ValueError(f"Invalid qrels row in {path}: {line.rstrip()}")
            query_id, document_id, score = fields[:3]
            qrels[query_id][document_id] = int(score)
    return dict(qrels)


def _distinct_document_ids(ranked_chunks: list) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for result in ranked_chunks:
        if result.record.document_id not in seen:
            seen.add(result.record.document_id)
            ordered.append(result.record.document_id)
    return ordered


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _average_precision_at_k(
    ranked_document_ids: list[str], relevant: dict[str, int], k: int
) -> float:
    hits = 0
    precision_sum = 0.0
    for rank, document_id in enumerate(ranked_document_ids[:k], start=1):
        if document_id in relevant:
            hits += 1
            precision_sum += hits / rank
    denominator = min(len(relevant), k)
    return precision_sum / denominator if denominator else 0.0


def _ndcg_at_k(
    ranked_relevance: list[int], ideal_relevance: list[int], k: int
) -> float:
    def dcg(values: list[int]) -> float:
        return sum(
            ((2**grade) - 1) / math.log2(rank + 1)
            for rank, grade in enumerate(values[:k], start=1)
        )

    actual = dcg(ranked_relevance)
    ideal = dcg(sorted(ideal_relevance, reverse=True))
    return actual / ideal if ideal else 0.0


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * (percentile / 100)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight)
