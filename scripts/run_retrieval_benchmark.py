"""Run GroundDesk retrieval against a standard BEIR-format benchmark.

Example:
    python scripts/run_retrieval_benchmark.py --download nfcorpus --modes sparse,hybrid
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import urlopen
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evals.benchmark import (  # noqa: E402
    build_benchmark_index,
    build_benchmark_report,
    evaluate_retrieval_strategy,
    load_beir_dataset,
    make_retriever,
    report_as_markdown,
    select_labelled_slice,
)
from app.retrieval.embeddings import EmbeddingModel  # noqa: E402


BEIR_DOWNLOADS = {
    "nfcorpus": {
        "url": "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/nfcorpus.zip",
        "md5": "a89dba18a62ef92f7d323ec890a0d38d",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate GroundDesk retrieval against BEIR relevance labels."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("benchmarks/data/nfcorpus"),
        help="Extracted BEIR dataset directory.",
    )
    parser.add_argument(
        "--download",
        choices=sorted(BEIR_DOWNLOADS),
        help="Download and extract an official small BEIR dataset before evaluation.",
    )
    parser.add_argument("--split", default="test")
    parser.add_argument(
        "--modes",
        default="sparse,hybrid",
        help="Comma-separated GroundDesk retrieval modes: sparse,dense,hybrid,adaptive.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=("hashing", "sentence-transformers", "gemini"),
        default="hashing",
    )
    parser.add_argument("--embedding-model", default="hashing")
    parser.add_argument(
        "--embedding-dimensions",
        default="384",
        help="Comma-separated vector dimensions, primarily for hashing/Gemini.",
    )
    parser.add_argument(
        "--final-reranker",
        choices=("none", "lexical", "cross-encoder"),
        default="lexical",
    )
    parser.add_argument("--embedding-batch-size", type=int, default=64)
    parser.add_argument(
        "--query-limit",
        type=int,
        help="Development-only query cap; omit for a full reported benchmark.",
    )
    parser.add_argument(
        "--allow-gemini-corpus-embedding",
        action="store_true",
        help="Required acknowledgement before embedding a benchmark corpus through the paid/API provider.",
    )
    parser.add_argument(
        "--sample-queries",
        type=int,
        help="Evaluate a reproducibly sampled labelled query slice instead of the full dataset.",
    )
    parser.add_argument(
        "--sample-corpus-documents",
        type=int,
        default=250,
        help="Corpus size for --sample-queries; retains all relevant qrel documents and samples distractors.",
    )
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument(
        "--gemini-request-delay-seconds",
        type=float,
        default=1.1,
        help="Delay after each Gemini embedding API request to reduce free-tier rate-limit failures.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/retrieval_benchmark.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("results/retrieval_benchmark.md"),
    )
    parser.add_argument(
        "--publish-summary",
        type=Path,
        help="Optional compact JSON artifact for the public demo; excludes per-query failure details.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.download:
        _download_beir_dataset(args.download, args.dataset_dir)
    if args.embedding_provider == "gemini" and not args.allow_gemini_corpus_embedding:
        raise SystemExit(
            "Gemini would embed the entire benchmark corpus. Re-run with "
            "--allow-gemini-corpus-embedding only after accepting API cost/latency, "
            "or use local sentence-transformers."
        )

    modes = tuple(item.strip().lower() for item in args.modes.split(",") if item.strip())
    invalid_modes = set(modes) - {"sparse", "dense", "hybrid", "adaptive"}
    if invalid_modes:
        raise SystemExit(f"Unsupported retrieval modes: {', '.join(sorted(invalid_modes))}")
    dimensions = tuple(
        int(value.strip()) for value in args.embedding_dimensions.split(",") if value.strip()
    )
    dataset = load_beir_dataset(args.dataset_dir, split=args.split)
    if args.sample_queries:
        dataset = select_labelled_slice(
            dataset,
            query_count=args.sample_queries,
            corpus_document_count=args.sample_corpus_documents,
            seed=args.sample_seed,
        )
    embeddings = EmbeddingModel(
        args.embedding_model,
        provider=args.embedding_provider,
        mrl_dimensions=dimensions,
        request_delay_seconds=(
            args.gemini_request_delay_seconds
            if args.embedding_provider == "gemini"
            else 0.0
        ),
    )

    with tempfile.TemporaryDirectory(prefix="grounddesk-benchmark-") as tmp_dir:
        print(
            f"Building isolated index for {len(dataset.documents):,} documents "
            f"using {args.embedding_model}..."
        )
        store, index_stats = build_benchmark_index(
            dataset,
            embeddings,
            index_dir=Path(tmp_dir) / "index",
            embedding_batch_size=args.embedding_batch_size,
            progress_callback=_progress_printer(),
        )
        if (
            args.embedding_provider == "sentence-transformers"
            and index_stats.embedding_backend != "sentence-transformers"
        ):
            raise SystemExit(
                "The requested sentence-transformers model did not load; refusing "
                "to report a silent hashing fallback as a semantic benchmark."
            )
        if args.embedding_provider == "gemini" and index_stats.embedding_backend != "gemini":
            raise SystemExit(
                "The requested Gemini embedding backend is unavailable; benchmark aborted."
            )

        runs = []
        for mode in modes:
            print(f"Evaluating {mode} retrieval on {dataset.name}...")
            retriever = make_retriever(
                mode=mode,
                store=store,
                embeddings=embeddings,
                final_reranker=args.final_reranker,
            )
            runs.append(
                evaluate_retrieval_strategy(
                    dataset,
                    retriever=retriever,
                    embeddings=embeddings,
                    strategy=f"{mode}+{args.final_reranker}",
                    query_limit=args.query_limit,
                )
            )
        report = build_benchmark_report(
            dataset, index_stats, runs, query_limit=args.query_limit
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.report.write_text(report_as_markdown(report), encoding="utf-8")
    if args.publish_summary:
        args.publish_summary.parent.mkdir(parents=True, exist_ok=True)
        args.publish_summary.write_text(
            json.dumps(_public_summary(report), indent=2) + "\n", encoding="utf-8"
        )
    print(report_as_markdown(report))
    print(f"JSON details: {args.output}")
    print(f"Markdown scorecard: {args.report}")
    if args.publish_summary:
        print(f"Public summary artifact: {args.publish_summary}")


def _progress_printer():
    last_percent = -1

    def print_progress(processed: int, total: int) -> None:
        nonlocal last_percent
        percent = int((processed / total) * 100) if total else 100
        bucket = (percent // 10) * 10
        if bucket > last_percent or processed == total:
            last_percent = bucket
            print(f"Embedding chunks: {processed:,}/{total:,} ({percent}%)")

    return print_progress


def _public_summary(report: dict) -> dict:
    public_report = {**report, "runs": []}
    for run in report["runs"]:
        public_report["runs"].append(
            {
                **{key: value for key, value in run.items() if key != "failures"},
                "failure_count": len(run.get("failures", [])),
            }
        )
    return public_report


def _download_beir_dataset(name: str, destination: Path) -> None:
    if (destination / "corpus.jsonl").exists():
        print(f"Dataset already present: {destination}")
        return
    specification = BEIR_DOWNLOADS[name]
    archive = destination.parent / f"{name}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {name} from the BEIR public dataset host...")
    with urlopen(specification["url"], timeout=120) as response, archive.open("wb") as target:
        shutil.copyfileobj(response, target)
    digest = hashlib.md5(archive.read_bytes()).hexdigest()
    if digest != specification["md5"]:
        archive.unlink(missing_ok=True)
        raise SystemExit(
            f"Downloaded archive checksum mismatch for {name}: {digest}; refusing to extract."
        )
    with zipfile.ZipFile(archive) as zip_file:
        root = destination.parent.resolve()
        for member in zip_file.infolist():
            extracted = (destination.parent / member.filename).resolve()
            if root not in extracted.parents and extracted != root:
                raise SystemExit("Dataset archive contains an unsafe path.")
        zip_file.extractall(destination.parent)
    archive.unlink(missing_ok=True)
    print(f"Extracted dataset to {destination}")


if __name__ == "__main__":
    main()
