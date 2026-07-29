from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .loaders import LoadedSection


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    position: int
    section_title: str | None = None
    section_path: tuple[str, ...] = ()
    page_number: int | None = None
    word_count: int = 0
    content_hash: str = ""


def chunk_text(
    text: str, document_id: str, max_words: int = 180, overlap_words: int = 35
) -> list[TextChunk]:
    section = LoadedSection(title=None, text=text, position=0)
    return chunk_sections(
        (section,), document_id, max_words=max_words, overlap_words=overlap_words
    )


def chunk_sections(
    sections: Iterable[LoadedSection],
    document_id: str,
    *,
    max_words: int = 180,
    overlap_words: int = 35,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    global_position = 0
    for section in sections:
        section_chunks = _chunk_section(
            section,
            document_id=document_id,
            start_position=global_position,
            max_words=max_words,
            overlap_words=overlap_words,
        )
        chunks.extend(section_chunks)
        global_position += len(section_chunks)
    return chunks


def _chunk_section(
    section: LoadedSection,
    *,
    document_id: str,
    start_position: int,
    max_words: int,
    overlap_words: int,
) -> list[TextChunk]:
    words = re.findall(r"\S+", section.text)
    if not words:
        return []
    chunks: list[TextChunk] = []
    start = 0
    position = start_position
    step = max(1, max_words - overlap_words)
    while start < len(words):
        end = min(len(words), start + max_words)
        chunk_words = words[start:end]
        chunk_text_value = " ".join(chunk_words)
        chunks.append(
            TextChunk(
                chunk_id=f"{document_id}:chunk:{position}",
                text=chunk_text_value,
                position=position,
                section_title=section.title,
                section_path=section.heading_path,
                page_number=section.page_number,
                word_count=len(chunk_words),
                content_hash=hashlib.sha256(
                    chunk_text_value.encode("utf-8")
                ).hexdigest(),
            )
        )
        if end == len(words):
            break
        start += step
        position += 1
    return chunks
