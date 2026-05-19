"""Sparse lexical retrieval using a compact in-memory BM25 index."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re

from .vector_store import ChunkRecord, SearchResult


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Tokenize while preserving support-relevant exact strings when possible."""
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


@dataclass
class _LexicalDocument:
    record: ChunkRecord
    term_frequencies: Counter[str]
    length: int


class BM25Index:
    """Small deterministic BM25 index suited to local development and tests."""

    def __init__(self, *, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[_LexicalDocument] = []
        self.document_frequencies: Counter[str] = Counter()
        self.average_document_length = 0.0

    def rebuild(self, records: list[ChunkRecord]) -> None:
        self.documents = []
        self.document_frequencies = Counter()
        total_length = 0

        for record in records:
            terms = tokenize(_record_text(record))
            term_frequencies = Counter(terms)
            length = len(terms)
            self.documents.append(
                _LexicalDocument(
                    record=record,
                    term_frequencies=term_frequencies,
                    length=length,
                )
            )
            total_length += length
            self.document_frequencies.update(term_frequencies.keys())

        self.average_document_length = (
            total_length / len(self.documents)
            if self.documents
            else 0.0
        )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not self.documents:
            return []

        query_terms = tokenize(query)
        if not query_terms:
            return []

        scored: list[tuple[_LexicalDocument, float]] = []
        for document in self.documents:
            score = sum(
                self._score_term(term, document)
                for term in query_terms
            )
            if score > 0:
                scored.append((document, score))

        if not scored:
            return []

        scored.sort(key=lambda item: item[1], reverse=True)
        max_score = scored[0][1]
        return [
            SearchResult(
                record=document.record,
                score=float(score / max_score) if max_score else 0.0,
            )
            for document, score in scored[:top_k]
        ]

    def _score_term(self, term: str, document: _LexicalDocument) -> float:
        frequency = document.term_frequencies.get(term, 0)
        if frequency == 0:
            return 0.0

        document_count = len(self.documents)
        containing_documents = self.document_frequencies.get(term, 0)
        inverse_document_frequency = math.log(
            1 + (document_count - containing_documents + 0.5) / (containing_documents + 0.5)
        )
        normalization = 1 - self.b + self.b * (
            document.length / self.average_document_length
            if self.average_document_length
            else 0.0
        )
        return inverse_document_frequency * (
            frequency * (self.k1 + 1)
        ) / (frequency + self.k1 * normalization)


def _record_text(record: ChunkRecord) -> str:
    section_path = " ".join(record.section_path)
    return " ".join(
        part
        for part in (
            record.title,
            record.section_title or "",
            section_path,
            record.text,
        )
        if part
    )
