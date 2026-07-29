"""Lightweight quality checks for deciding what should become retrievable evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .chunking import TextChunk
from .loaders import LoadedDocument, LoadedSection


@dataclass(frozen=True)
class QualityReport:
    warnings: tuple[str, ...]
    total_sections: int
    indexed_sections: int
    total_chunks: int
    indexed_chunks: int
    skipped_chunks: int
    empty_sections: int
    rejected: bool


def assess_sections(
    document: LoadedDocument, sections: tuple[LoadedSection, ...]
) -> tuple[tuple[LoadedSection, ...], list[str], int]:
    warnings: list[str] = []
    empty_sections = sum(1 for section in sections if not section.text.strip())
    usable_sections = tuple(section for section in sections if section.text.strip())

    if empty_sections:
        warnings.append(f"skipped_empty_sections:{empty_sections}")
    if document.source_type == "pdf" and not usable_sections:
        warnings.append("pdf_no_extractable_text_possible_ocr_needed")
    if document.source_type == "url" and _looks_like_low_value_url_page(document.text):
        warnings.append("url_content_looks_low_value_or_blocked")
    return usable_sections, warnings, empty_sections


def filter_chunks(
    chunks: list[TextChunk], *, min_words: int = 2
) -> tuple[list[TextChunk], list[str]]:
    indexed: list[TextChunk] = []
    warnings: list[str] = []
    skipped_short = 0
    for chunk in chunks:
        if chunk.word_count < min_words:
            skipped_short += 1
            continue
        indexed.append(chunk)
    if skipped_short:
        warnings.append(f"skipped_short_chunks:{skipped_short}")
    return indexed, warnings


def build_report(
    *,
    warnings: list[str],
    total_sections: int,
    indexed_sections: int,
    total_chunks: int,
    indexed_chunks: int,
    empty_sections: int,
) -> QualityReport:
    rejected = indexed_chunks == 0
    if rejected:
        warnings = [*warnings, "no_retrievable_chunks_indexed"]
    return QualityReport(
        warnings=tuple(dict.fromkeys(warnings)),
        total_sections=total_sections,
        indexed_sections=indexed_sections,
        total_chunks=total_chunks,
        indexed_chunks=indexed_chunks,
        skipped_chunks=total_chunks - indexed_chunks,
        empty_sections=empty_sections,
        rejected=rejected,
    )


def _looks_like_low_value_url_page(text: str) -> bool:
    lowered = re.sub(r"\s+", " ", text.lower()).strip()
    signals = [
        "javascript is disabled",
        "enable javascript",
        "sign in to continue",
        "access denied",
        "unsupported browser",
        "please log in",
    ]
    return any(signal in lowered for signal in signals)
