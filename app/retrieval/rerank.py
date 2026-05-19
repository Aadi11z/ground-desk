"""Final reranker hooks."""

from __future__ import annotations

from dataclasses import dataclass

from .lexical import tokenize
from .vector_store import SearchResult


class FinalReranker:
    def rerank(self, query: str, candidates: list[SearchResult], *, top_k: int) -> list[SearchResult]:
        return candidates[:top_k]


@dataclass
class LexicalFinalReranker(FinalReranker):
    semantic_weight: float = 0.75
    lexical_weight: float = 0.25

    def rerank(self, query: str, candidates: list[SearchResult], *, top_k: int) -> list[SearchResult]:
        query_terms = set(tokenize(query))
        reranked = []
        for candidate in candidates:
            candidate_terms = set(tokenize(candidate.record.text))
            overlap = len(query_terms.intersection(candidate_terms)) / max(1, len(query_terms))
            score = self.semantic_weight * candidate.score + self.lexical_weight * overlap
            reranked.append(SearchResult(record=candidate.record, score=float(min(1.0, score))))
        reranked.sort(key=lambda result: result.score, reverse=True)
        return reranked[:top_k]


class CrossEncoderFinalReranker(FinalReranker):
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: list[SearchResult], *, top_k: int) -> list[SearchResult]:
        if not candidates:
            return []
        scores = self.model.predict([(query, candidate.record.text) for candidate in candidates])
        ranked = [
            SearchResult(record=candidate.record, score=float(score))
            for candidate, score in zip(candidates, scores, strict=True)
        ]
        ranked.sort(key=lambda result: result.score, reverse=True)
        max_score = max(result.score for result in ranked) or 1.0
        return [
            SearchResult(
                record=result.record,
                score=float(max(0.0, min(1.0, result.score / max_score))),
            )
            for result in ranked[:top_k]
        ]


def create_final_reranker(kind: str, *, cross_encoder_model: str) -> FinalReranker:
    normalized = kind.lower()
    if normalized == "none":
        return FinalReranker()
    if normalized == "cross-encoder":
        try:
            return CrossEncoderFinalReranker(cross_encoder_model)
        except Exception:
            return LexicalFinalReranker()
    return LexicalFinalReranker()
