"""Embedding providers and multi-representation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
import re
import time
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: dict[str, np.ndarray]

    @property
    def dimensions(self) -> dict[str, int]:
        return {
            name: int(matrix.shape[1])
            for name, matrix in self.vectors.items()
            if matrix.ndim == 2
        }

    @property
    def default_name(self) -> str:
        return min(self.dimensions, key=self.dimensions.get)

    @property
    def largest_name(self) -> str:
        return max(self.dimensions, key=self.dimensions.get)


class EmbeddingModel:
    """Use Gemini MRL when configured, otherwise fall back to local embeddings.

    Document and query APIs return every available vector representation so
    ingestion and retrieval can select the appropriate embedding size.
    """

    def __init__(
        self,
        model_name: str,
        *,
        provider: str = "auto",
        mrl_dimensions: tuple[int, ...] | None = None,
        api_key: str | None = None,
        request_delay_seconds: float = 0.0,
        max_attempts: int = 4,
        retry_base_seconds: float = 2.0,
        sleep=time.sleep,
    ):
        self.model_name = model_name
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.request_delay_seconds = max(0.0, request_delay_seconds)
        self.max_attempts = max(1, max_attempts)
        self.retry_base_seconds = max(0.0, retry_base_seconds)
        self.sleep = sleep
        requested_dimensions = tuple(sorted(mrl_dimensions or (768, 1536, 3072)))
        self.backend = "hashing"
        self._model = None
        self._sentence_model_name: str | None = None
        self._gemini_client = None

        if self._should_use_gemini():
            try:
                from google import genai

                self._gemini_client = genai.Client(api_key=self.api_key)
                self.backend = "gemini"
                self.mrl_dimensions = requested_dimensions
                return
            except Exception:
                self._gemini_client = None

        if (
            self.model_name.startswith("gemini-embedding")
            and self._gemini_client is None
        ):
            self.mrl_dimensions = (384,)
            return

        if model_name not in {"", "hashing", "unit-test", None}:
            self._sentence_model_name = model_name
            self.backend = "sentence-transformers"

        if self.model_name in {"hashing", "unit-test"} and mrl_dimensions:
            self.mrl_dimensions = requested_dimensions
        else:
            self.mrl_dimensions = (384,)

    @property
    def supports_mrl(self) -> bool:
        return self.backend == "gemini" and len(self.mrl_dimensions) > 1

    @property
    def vector_names(self) -> tuple[str, ...]:
        return tuple(f"dense_{dimension}" for dimension in self.mrl_dimensions)

    def encode_documents(
        self, texts: Iterable[str], titles: Iterable[str] | None = None
    ) -> EmbeddingBatch:
        return self._encode(texts, task_type="RETRIEVAL_DOCUMENT", titles=titles)

    def encode_queries(self, texts: Iterable[str]) -> EmbeddingBatch:
        return self._encode(texts, task_type="RETRIEVAL_QUERY")

    def _encode(
        self,
        texts: Iterable[str],
        *,
        task_type: str,
        titles: Iterable[str] | None = None,
    ) -> EmbeddingBatch:
        text_list = list(texts)
        title_list = list(titles) if titles is not None else [None] * len(text_list)
        if not text_list:
            return EmbeddingBatch(
                {
                    f"dense_{dimension}": np.empty((0, dimension), dtype=np.float32)
                    for dimension in self.mrl_dimensions
                }
            )

        if self._gemini_client is not None:
            largest_dimension = max(self.mrl_dimensions)
            full = self._encode_with_gemini(
                text_list,
                task_type=task_type,
                titles=title_list,
                output_dimensionality=largest_dimension,
            )
            return EmbeddingBatch(
                {
                    f"dense_{dimension}": _normalize_rows(full[:, :dimension])
                    for dimension in self.mrl_dimensions
                }
            )

        self._ensure_sentence_model()
        if self._model is not None:
            vectors = self._model.encode(
                text_list, normalize_embeddings=True, show_progress_bar=False
            )
            matrix = np.asarray(vectors, dtype=np.float32)
            return EmbeddingBatch({f"dense_{matrix.shape[1]}": matrix})

        matrices = {
            f"dense_{dimension}": np.vstack(
                [_hash_embed(text, dimension) for text in text_list]
            ).astype(np.float32)
            for dimension in self.mrl_dimensions
        }
        return EmbeddingBatch(matrices)

    def _encode_with_gemini(
        self,
        texts: list[str],
        *,
        task_type: str,
        titles: list[str | None],
        output_dimensionality: int,
    ) -> np.ndarray:
        from google.genai import types

        vectors = []
        for text, title in zip(texts, titles, strict=True):
            content = text
            config_kwargs = {"output_dimensionality": output_dimensionality}
            if self._uses_embedding_2():
                content = _format_embedding_2_content(
                    text, task_type=task_type, title=title
                )
            else:
                config_kwargs["task_type"] = task_type
                if task_type == "RETRIEVAL_DOCUMENT" and title:
                    config_kwargs["title"] = title
            for attempt in range(1, self.max_attempts + 1):
                try:
                    result = self._gemini_client.models.embed_content(
                        model=self.model_name,
                        contents=content,
                        config=types.EmbedContentConfig(**config_kwargs),
                    )
                    break
                except Exception as exc:
                    if (
                        not _is_retryable_gemini_error(exc)
                        or attempt >= self.max_attempts
                    ):
                        raise
                    fallback_delay = self.retry_base_seconds * (2 ** (attempt - 1))
                    self.sleep(_retry_delay_seconds(exc, fallback=fallback_delay))
            embedding = result.embeddings[0]
            vectors.append(np.asarray(embedding.values, dtype=np.float32))
            if self.request_delay_seconds:
                self.sleep(self.request_delay_seconds)
        return _normalize_rows(np.vstack(vectors))

    def _uses_embedding_2(self) -> bool:
        return self.model_name == "gemini-embedding-2"

    def _should_use_gemini(self) -> bool:
        if self.provider == "gemini":
            return True
        if self.provider != "auto":
            return False
        return self.model_name.startswith("gemini-embedding") and bool(self.api_key)

    def _ensure_sentence_model(self) -> None:
        if self._model is not None or self._sentence_model_name is None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._sentence_model_name)
        except Exception:
            self.backend = "hashing"
            self._model = None
        finally:
            self._sentence_model_name = None


def _hash_embed(text: str, dims: int) -> np.ndarray:
    vector = np.zeros(dims, dtype=np.float32)
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(float(np.dot(vector, vector)))
    if norm:
        vector /= norm
    return vector


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _format_embedding_2_content(
    text: str, *, task_type: str, title: str | None = None
) -> str:
    if task_type == "RETRIEVAL_DOCUMENT":
        document_title = title or "none"
        return f"title: {document_title} | text: {text}"
    if task_type == "RETRIEVAL_QUERY":
        return f"task: question answering | query: {text}"
    return text


def _is_retryable_gemini_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code not in {429, 500, 502, 503, 504}:
        return False
    return "RequestsPerDayPerProjectPerModel" not in str(exc)


def _retry_delay_seconds(exc: Exception, *, fallback: float) -> float:
    message = str(getattr(exc, "message", "") or exc)
    match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", message, re.I)
    if match:
        return max(fallback, float(match.group(1)) + 1.0)
    match = re.search(r"retryDelay['\" ]*:\s*['\"]?([0-9]+)s", message, re.I)
    if match:
        return max(fallback, float(match.group(1)) + 1.0)
    return fallback
