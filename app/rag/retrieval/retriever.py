"""High-level retrieval orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from app.core.config import Settings
from app.domain.tenancy import TenantScope

from .adaptive import AdaptiveQueryPlanner, RetrievalPlan, StructuredQueryPlanner
from .compression import compress_results
from .lexical import BM25Index
from .rerank import create_final_reranker
from .vector_store import SearchResult, VectorStoreBackend

RetrievalMode = Literal["dense", "sparse", "hybrid"]


@dataclass(frozen=True)
class RetrievalDiagnostics:
    mode: RetrievalMode
    dense_candidates: int
    sparse_candidates: int
    reranked_candidates: int
    query_count: int = 1
    used_hyde: bool = False
    rewritten_query: str | None = None
    planner: str = "static"
    planner_reason: str | None = None
    planner_fallback: bool = False


class HybridRetriever:
    """Combine dense semantic search with sparse lexical search.

    The retriever owns ranking policy; storage backends only provide candidate
    access. This keeps later reranking, routing, and metadata filters additive.
    """

    def __init__(self, settings: Settings, store: VectorStoreBackend, embeddings=None):
        self.settings = settings
        self.store = store
        self.embeddings = embeddings
        self.lexical_index = BM25Index()
        self.rules_planner = AdaptiveQueryPlanner(
            multi_query_limit=settings.multi_query_limit
        )
        self.planner = self.rules_planner
        if (
            settings.retrieval_mode.lower() == "planned"
            and settings.query_planner_provider.lower() == "gemini"
        ):
            from app.rag.generation.llm import get_generation_provider

            self.planner = StructuredQueryPlanner(
                get_generation_provider(
                    max_attempts=settings.gemini_generation_max_attempts,
                    retry_base_seconds=settings.gemini_generation_retry_base_seconds,
                    request_delay_seconds=settings.gemini_generation_request_delay_seconds,
                ),
                model=settings.query_planner_model,
                multi_query_limit=settings.multi_query_limit,
            )
        self.final_reranker = create_final_reranker(
            settings.final_reranker,
            cross_encoder_model=settings.cross_encoder_model,
        )
        self._corpus_signature: tuple[str, tuple[tuple[str, str], ...]] | None = None
        self.last_diagnostics = RetrievalDiagnostics(
            mode=self._mode(),
            dense_candidates=0,
            sparse_candidates=0,
            reranked_candidates=0,
            rewritten_query=None,
        )

    def retrieve(
        self,
        scope: TenantScope,
        query: str,
        query_embeddings: dict[str, np.ndarray] | np.ndarray | None = None,
        top_k: int = 5,
        *,
        query_embedding: np.ndarray | None = None,
        document_ids: set[str] | None = None,
    ) -> list[SearchResult]:
        query_embeddings = _coerce_query_embeddings(
            query_embeddings=query_embeddings,
            query_embedding=query_embedding,
        )
        configured_mode = self.settings.retrieval_mode.lower()
        if configured_mode == "planned" and isinstance(
            self.planner, StructuredQueryPlanner
        ):
            plan = self.planner.plan(query)
        elif self.settings.adaptive_retrieval_enabled and configured_mode == "adaptive":
            plan = self.rules_planner.plan(query)
        else:
            plan = self._static_plan(query)
        mode = self._mode(plan.mode)
        coarse_vector_name = _select_query_vector_name(
            query_embeddings,
            preferred=getattr(self.store, "default_vector_name", None),
        )
        dense_results = []
        sparse_results = []
        for search_query in plan.search_queries:
            search_embeddings = self._embeddings_for(
                search_query, fallback=query_embeddings
            )
            dense_results.extend(
                self._search_dense(
                    _query_vector(search_embeddings, coarse_vector_name),
                    scope=scope,
                    top_k=max(top_k, self.settings.coarse_candidate_k),
                    vector_name=coarse_vector_name,
                    document_ids=document_ids,
                )
                if mode in {"dense", "hybrid"}
                else []
            )
            sparse_results.extend(
                self._search_sparse(
                    search_query,
                    top_k=max(top_k, self.settings.sparse_candidate_k),
                    scope=scope,
                    document_ids=document_ids,
                )
                if mode in {"sparse", "hybrid"}
                else []
            )
        if plan.use_hyde and mode in {"dense", "hybrid"}:
            hyde_embeddings = self._embeddings_for(
                self.planner.hyde_query(plan.rewritten_query),
                fallback=query_embeddings,
            )
            dense_results.extend(
                self._search_dense(
                    _query_vector(hyde_embeddings, coarse_vector_name),
                    scope=scope,
                    top_k=max(top_k, self.settings.coarse_candidate_k),
                    vector_name=coarse_vector_name,
                    document_ids=document_ids,
                )
            )
        dense_results = _dedupe_best(dense_results)
        sparse_results = _dedupe_best(sparse_results)
        self.last_diagnostics = RetrievalDiagnostics(
            mode=mode,
            dense_candidates=len(dense_results),
            sparse_candidates=len(sparse_results),
            reranked_candidates=0,
            query_count=len(plan.search_queries),
            used_hyde=plan.use_hyde,
            rewritten_query=plan.rewritten_query,
            planner=plan.planner,
            planner_reason=plan.planner_reason,
            planner_fallback=plan.planner_fallback,
        )

        if mode == "dense":
            reranked = self._rerank_if_possible(
                scope,
                dense_results,
                query_embeddings,
                top_k=max(top_k, self.settings.dense_candidate_k),
            )
            return self._finalize_results(
                scope,
                query,
                self._final_rerank(query, reranked, top_k=top_k),
                top_k=top_k,
            )
        if mode == "sparse":
            return self._finalize_results(
                scope,
                query,
                self._final_rerank(query, sparse_results, top_k=top_k),
                top_k=top_k,
            )
        fused = _reciprocal_rank_fusion(
            dense_results,
            sparse_results,
            top_k=max(top_k, self.settings.dense_candidate_k),
            reciprocal_rank_k=self.settings.reciprocal_rank_k,
            dense_weight=self.settings.dense_rrf_weight,
            sparse_weight=self.settings.sparse_rrf_weight,
        )
        reranked = self._rerank_if_possible(
            scope,
            fused,
            query_embeddings,
            top_k=max(top_k, self.settings.dense_candidate_k),
        )
        return self._finalize_results(
            scope,
            query,
            self._final_rerank(query, reranked, top_k=top_k),
            top_k=top_k,
        )

    def _search_sparse(
        self,
        query: str,
        top_k: int,
        *,
        scope: TenantScope,
        document_ids: set[str] | None = None,
    ) -> list[SearchResult]:
        self._refresh_lexical_index_if_needed(scope)
        results = self.lexical_index.search(
            query, top_k=max(top_k, self.settings.sparse_candidate_k)
        )
        if document_ids is not None:
            results = [
                result
                for result in results
                if result.record.document_id in document_ids
            ]
        return results[:top_k]

    def _refresh_lexical_index_if_needed(self, scope: TenantScope) -> None:
        signature = self._current_corpus_signature(scope)
        if signature == self._corpus_signature:
            return
        records = self.store.list_chunks(scope)
        self.lexical_index.rebuild(records)
        self._corpus_signature = signature

    def _current_corpus_signature(
        self, scope: TenantScope
    ) -> tuple[str, tuple[tuple[str, str], ...]]:
        if hasattr(self.store, "list_documents"):
            documents = self.store.list_documents(scope)
            if documents:
                return (
                    scope.workspace_id,
                    tuple(
                        sorted(
                            (
                                document.document_id,
                                f"{document.version_id}:{document.chunks_indexed}",
                            )
                            for document in documents
                        )
                    ),
                )
        records = self.store.list_chunks(scope)
        return (
            scope.workspace_id,
            tuple(
                sorted(
                    (record.chunk_id, record.content_hash or record.text)
                    for record in records
                )
            ),
        )

    def _mode(self, override: str | None = None) -> RetrievalMode:
        mode = (override or self.settings.retrieval_mode).lower()
        if mode in {"adaptive", "planned"}:
            mode = "hybrid"
        if mode not in {"dense", "sparse", "hybrid"}:
            raise ValueError(
                f"Unsupported retrieval mode: {self.settings.retrieval_mode}. "
                "Use planned, adaptive, dense, sparse, or hybrid."
            )
        return mode

    def _static_plan(self, query: str) -> RetrievalPlan:
        analysis = self.rules_planner.analyze(query)
        return RetrievalPlan(
            mode="hybrid"
            if self.settings.retrieval_mode.lower() in {"adaptive", "planned"}
            else self.settings.retrieval_mode,
            rewritten_query=query,
            search_queries=(query,),
            use_hyde=False,
            analysis=analysis,
            planner="static",
            planner_reason="original_query",
        )

    def _rerank_if_possible(
        self,
        scope: TenantScope,
        candidates: list[SearchResult],
        query_embeddings: dict[str, np.ndarray],
        *,
        top_k: int,
    ) -> list[SearchResult]:
        largest_vector_name = getattr(self.store, "largest_vector_name", None)
        if (
            not candidates
            or not largest_vector_name
            or largest_vector_name == self.store.default_vector_name
            or largest_vector_name not in query_embeddings
        ):
            return candidates[:top_k]

        candidate_ids = [candidate.record.chunk_id for candidate in candidates]
        document_vectors = self.store.fetch_vectors(
            scope, candidate_ids, vector_name=largest_vector_name
        )
        if not document_vectors:
            return candidates[:top_k]

        query = _normalize(_query_vector(query_embeddings, largest_vector_name))
        rescored: list[SearchResult] = []
        for candidate in candidates:
            vector = document_vectors.get(candidate.record.chunk_id)
            if vector is None:
                continue
            score = float(np.dot(_normalize(vector), query))
            rescored.append(
                SearchResult(
                    record=candidate.record,
                    score=float(max(0.0, min(1.0, score))),
                )
            )
        rescored.sort(key=lambda result: result.score, reverse=True)
        self.last_diagnostics = RetrievalDiagnostics(
            mode=self.last_diagnostics.mode,
            dense_candidates=self.last_diagnostics.dense_candidates,
            sparse_candidates=self.last_diagnostics.sparse_candidates,
            reranked_candidates=len(rescored),
            query_count=self.last_diagnostics.query_count,
            used_hyde=self.last_diagnostics.used_hyde,
            rewritten_query=self.last_diagnostics.rewritten_query,
            planner=self.last_diagnostics.planner,
            planner_reason=self.last_diagnostics.planner_reason,
            planner_fallback=self.last_diagnostics.planner_fallback,
        )
        return rescored[:top_k]

    def _compress(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        return compress_results(
            query,
            results,
            max_sentences=self.settings.context_max_sentences,
        )

    def _finalize_results(
        self,
        scope: TenantScope,
        query: str,
        results: list[SearchResult],
        *,
        top_k: int,
    ) -> list[SearchResult]:
        return self._compress(query, results)

    def _embeddings_for(
        self,
        query: str,
        *,
        fallback: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:
        if self.embeddings is None:
            return fallback
        return self.embeddings.encode_queries([query]).vectors

    def _final_rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        top_k: int,
    ) -> list[SearchResult]:
        return self.final_reranker.rerank(query, candidates, top_k=top_k)

    def _search_dense(
        self,
        query_embedding: np.ndarray,
        *,
        scope: TenantScope,
        top_k: int,
        vector_name: str,
        document_ids: set[str] | None = None,
    ) -> list[SearchResult]:
        return self.store.search(
            scope,
            query_embedding,
            top_k=top_k,
            vector_name=vector_name,
            document_ids=document_ids,
        )


def _reciprocal_rank_fusion(
    dense_results: list[SearchResult],
    sparse_results: list[SearchResult],
    *,
    top_k: int,
    reciprocal_rank_k: int,
    dense_weight: float,
    sparse_weight: float,
) -> list[SearchResult]:
    fused_scores: dict[str, float] = {}
    records_by_id = {}

    for weight, results in (
        (dense_weight, dense_results),
        (sparse_weight, sparse_results),
    ):
        for rank, result in enumerate(results, start=1):
            chunk_id = result.record.chunk_id
            records_by_id[chunk_id] = result.record
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (
                weight / (reciprocal_rank_k + rank)
            )

    if not fused_scores:
        return []

    max_score = max(fused_scores.values())
    ranked_ids = sorted(
        fused_scores,
        key=lambda chunk_id: fused_scores[chunk_id],
        reverse=True,
    )[:top_k]
    return [
        SearchResult(
            record=records_by_id[chunk_id],
            score=float(fused_scores[chunk_id] / max_score) if max_score else 0.0,
        )
        for chunk_id in ranked_ids
    ]


def _smallest_vector_name(vectors: dict[str, np.ndarray]) -> str:
    return min(vectors, key=lambda name: vectors[name].shape[1])


def _select_query_vector_name(
    vectors: dict[str, np.ndarray], *, preferred: str | None
) -> str:
    if preferred in vectors:
        return str(preferred)
    return _smallest_vector_name(vectors)


def _query_vector(vectors: dict[str, np.ndarray], vector_name: str) -> np.ndarray:
    matrix = vectors[vector_name]
    return matrix[0] if matrix.ndim == 2 else matrix


def _normalize(vector: np.ndarray) -> np.ndarray:
    vector = vector.reshape(-1).astype(np.float32)
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def _coerce_query_embeddings(
    *,
    query_embeddings: dict[str, np.ndarray] | np.ndarray | None,
    query_embedding: np.ndarray | None,
) -> dict[str, np.ndarray]:
    if isinstance(query_embeddings, dict):
        return query_embeddings
    if isinstance(query_embeddings, np.ndarray):
        matrix = (
            query_embeddings.reshape(1, -1)
            if query_embeddings.ndim == 1
            else query_embeddings
        )
        return {f"dense_{matrix.shape[1]}": matrix}
    if query_embedding is not None:
        matrix = (
            query_embedding.reshape(1, -1)
            if query_embedding.ndim == 1
            else query_embedding
        )
        return {f"dense_{matrix.shape[1]}": matrix}
    raise ValueError("At least one query embedding representation is required.")


def _dedupe_best(results: list[SearchResult]) -> list[SearchResult]:
    best_by_chunk: dict[str, SearchResult] = {}
    for result in results:
        current = best_by_chunk.get(result.record.chunk_id)
        if current is None or result.score > current.score:
            best_by_chunk[result.record.chunk_id] = result
    return sorted(best_by_chunk.values(), key=lambda result: result.score, reverse=True)
