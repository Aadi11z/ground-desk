"""Deterministic context compression for retrieved evidence."""

from __future__ import annotations

import re

from .lexical import tokenize
from .vector_store import SearchResult


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def compress_results(
    query: str,
    results: list[SearchResult],
    *,
    max_sentences: int = 3,
) -> list[SearchResult]:
    query_terms = set(tokenize(query))
    compressed: list[SearchResult] = []
    for result in results:
        sentences = [sentence.strip() for sentence in SENTENCE_SPLIT.split(result.record.text) if sentence.strip()]
        if len(sentences) <= max_sentences:
            compressed.append(result)
            continue
        ranked_sentences = sorted(
            sentences,
            key=lambda sentence: len(query_terms.intersection(tokenize(sentence))),
            reverse=True,
        )
        chosen = ranked_sentences[:max_sentences]
        clone = type(result.record)(**{**result.record.__dict__, "text": " ".join(chosen)})
        compressed.append(SearchResult(record=clone, score=result.score))
    return compressed
