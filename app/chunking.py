from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    position: int


def chunk_text(text: str, document_id: str, max_words: int = 180, overlap_words: int = 35) -> list[TextChunk]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks: list[TextChunk] = []
    start = 0
    position = 0
    step = max(1, max_words - overlap_words)
    while start < len(words):
        end = min(len(words), start + max_words)
        chunk_words = words[start:end]
        chunks.append(
            TextChunk(
                chunk_id=f"{document_id}:chunk:{position}",
                text=" ".join(chunk_words),
                position=position,
            )
        )
        if end == len(words):
            break
        start += step
        position += 1
    return chunks

