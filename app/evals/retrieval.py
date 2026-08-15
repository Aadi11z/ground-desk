"""Retrieval evaluation utilities for ranking regressions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.rag.retrieval.embeddings import EmbeddingModel
from app.rag.retrieval.retriever import HybridRetriever

from . import EVALUATION_SCOPE


@dataclass(frozen=True)
class RetrievalEvalCase:
    question: str
    relevant_titles: tuple[str, ...]


RETRIEVAL_GOLDEN_SET = [
    RetrievalEvalCase(
        "How long do password reset emails take?",
        ("Authentication And SSO",),
    ),
    RetrievalEvalCase(
        "Where can I download invoices?",
        ("Billing And Invoices",),
    ),
    RetrievalEvalCase(
        "What happens when an invite link expires?",
        ("Product Usage",),
    ),
    RetrievalEvalCase(
        "How do I troubleshoot SSO sign-in failures?",
        ("Authentication And SSO",),
    ),
]


def run_retrieval_evals(
    retriever: HybridRetriever,
    embeddings: EmbeddingModel,
    *,
    top_k: int = 5,
) -> dict:
    results = []
    recall_hits = 0
    reciprocal_ranks = []
    ndcg_scores = []

    for case in RETRIEVAL_GOLDEN_SET:
        vectors = embeddings.encode_queries([case.question]).vectors
        ranked = retriever.retrieve(
            EVALUATION_SCOPE, case.question, vectors, top_k=top_k
        )
        ranked_titles = [result.record.title for result in ranked]
        relevance = [
            1 if title in case.relevant_titles else 0 for title in ranked_titles
        ]
        first_relevant_rank = next(
            (index for index, value in enumerate(relevance, start=1) if value),
            None,
        )
        recall_hit = first_relevant_rank is not None
        recall_hits += int(recall_hit)
        reciprocal_ranks.append(1 / first_relevant_rank if first_relevant_rank else 0.0)
        ndcg_scores.append(_ndcg(relevance))
        results.append(
            {
                "question": case.question,
                "relevant_titles": list(case.relevant_titles),
                "ranked_titles": ranked_titles,
                "recall_hit": recall_hit,
                "first_relevant_rank": first_relevant_rank,
            }
        )

    total = len(RETRIEVAL_GOLDEN_SET)
    return {
        "num_cases": total,
        f"recall@{top_k}": recall_hits / total if total else 0.0,
        "mrr": sum(reciprocal_ranks) / total if total else 0.0,
        "ndcg": sum(ndcg_scores) / total if total else 0.0,
        "results": results,
    }


def _ndcg(relevance: list[int]) -> float:
    if not relevance:
        return 0.0
    dcg = sum(
        value / math.log2(index + 1) for index, value in enumerate(relevance, start=1)
    )
    ideal = sorted(relevance, reverse=True)
    idcg = sum(
        value / math.log2(index + 1) for index, value in enumerate(ideal, start=1)
    )
    return dcg / idcg if idcg else 0.0
