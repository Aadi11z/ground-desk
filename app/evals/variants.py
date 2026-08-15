"""Compare retrieval variants against the retrieval golden set."""

from __future__ import annotations

from app.rag.retrieval.retriever import HybridRetriever

from .retrieval import run_retrieval_evals


def compare_retrieval_variants(agent) -> dict:
    variants = {}
    for mode in ("dense", "hybrid", "adaptive"):
        settings = agent.settings.model_copy(update={"retrieval_mode": mode})
        retriever = HybridRetriever(settings, agent.store, embeddings=agent.embeddings)
        variants[mode] = run_retrieval_evals(retriever, agent.embeddings)
    return {"variants": variants}
