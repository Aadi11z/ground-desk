"""Persistent local storage for document manifests, chunks, and dense vectors."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Protocol
import uuid

import numpy as np


@dataclass
class DocumentManifest:
    document_id: str
    source_id: str
    version_id: str
    content_hash: str
    title: str
    source_type: str
    source: str
    original_filename: str | None
    chunks_indexed: int
    ingested_at: str
    status: str = "indexed"
    warnings: tuple[str, ...] = ()
    diagnostics: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ChunkRecord:
    chunk_id: str
    document_id: str
    version_id: str
    title: str
    source_type: str
    source: str
    text: str
    position: int
    section_title: str | None = None
    section_path: tuple[str, ...] = ()
    page_number: int | None = None
    word_count: int = 0
    content_hash: str = ""


@dataclass
class SearchResult:
    record: ChunkRecord
    score: float


class VectorStoreBackend(Protocol):
    @property
    def embedding_dimension(self) -> int | None:
        ...

    @property
    def vector_dimensions(self) -> dict[str, int]:
        ...

    @property
    def default_vector_name(self) -> str | None:
        ...

    @property
    def largest_vector_name(self) -> str | None:
        ...

    def has_records(self) -> bool:
        ...

    def count_chunks(self) -> int:
        ...

    def list_chunks(self) -> list[ChunkRecord]:
        ...

    def list_documents(self) -> list[DocumentManifest]:
        ...

    def get_document(self, document_id: str) -> DocumentManifest | None:
        ...

    def register_embedding_space(
        self,
        *,
        model_name: str,
        backend: str,
        dimensions: dict[str, int],
        default_vector_name: str,
    ) -> None:
        ...

    def upsert_document(
        self,
        document: DocumentManifest,
        records: list[ChunkRecord],
        embeddings: dict[str, np.ndarray],
    ) -> None:
        ...

    def delete_document(self, document_id: str) -> int:
        ...

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        *,
        vector_name: str | None = None,
        document_ids: set[str] | None = None,
    ) -> list[SearchResult]:
        ...

    def fetch_vectors(self, chunk_ids: list[str], *, vector_name: str) -> dict[str, np.ndarray]:
        ...


class LocalVectorStore:
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.documents: dict[str, DocumentManifest] = {}
        self.records: list[ChunkRecord] = []
        self.vectors: dict[str, np.ndarray] = {}
        self.index_metadata: dict[str, Any] = {}
        self.load()

    @property
    def embedding_dimension(self) -> int | None:
        default = self.default_vector_name
        return self.vector_dimensions.get(default) if default else None

    @property
    def vector_dimensions(self) -> dict[str, int]:
        if self.index_metadata.get("vector_dimensions"):
            return {
                str(name): int(dimension)
                for name, dimension in self.index_metadata["vector_dimensions"].items()
            }
        return {
            name: int(matrix.shape[1])
            for name, matrix in self.vectors.items()
            if matrix.ndim == 2
        }

    @property
    def default_vector_name(self) -> str | None:
        configured = self.index_metadata.get("default_vector_name")
        if configured:
            return str(configured)
        if self.vector_dimensions:
            return min(self.vector_dimensions, key=self.vector_dimensions.get)
        return None

    @property
    def largest_vector_name(self) -> str | None:
        if self.vector_dimensions:
            return max(self.vector_dimensions, key=self.vector_dimensions.get)
        return None

    @property
    def embeddings(self) -> np.ndarray:
        """Compatibility view over the configured default vector field."""
        default = self.default_vector_name
        if default and default in self.vectors:
            return self.vectors[default]
        return np.empty((0, 384), dtype=np.float32)

    def has_records(self) -> bool:
        return bool(self.records)

    def count_chunks(self) -> int:
        return len(self.records)

    def list_chunks(self) -> list[ChunkRecord]:
        return list(self.records)

    def list_documents(self) -> list[DocumentManifest]:
        if self.documents:
            return list(self.documents.values())
        return list(_reconstruct_documents(self.list_chunks()).values())

    def get_document(self, document_id: str) -> DocumentManifest | None:
        document = self.documents.get(document_id)
        if document is not None:
            return document
        return _reconstruct_documents(self.list_chunks()).get(document_id)

    @property
    def documents_path(self) -> Path:
        return self.index_dir / "documents.json"

    @property
    def metadata_path(self) -> Path:
        return self.index_dir / "chunks.json"

    @property
    def vectors_path(self) -> Path:
        return self.index_dir / "vectors.npy"

    @property
    def index_metadata_path(self) -> Path:
        return self.index_dir / "index_metadata.json"

    def load(self) -> None:
        if self.metadata_path.exists():
            raw_records = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            self.records = [_chunk_from_payload(item) for item in raw_records]
        if self.documents_path.exists():
            raw_documents = json.loads(self.documents_path.read_text(encoding="utf-8"))
            self.documents = {
                item["document_id"]: _document_from_payload(item)
                for item in raw_documents
            }
        elif self.records:
            self.documents = _reconstruct_documents(self.records)
        if self.index_metadata_path.exists():
            self.index_metadata = json.loads(self.index_metadata_path.read_text(encoding="utf-8"))
        if self.index_metadata.get("vector_dimensions"):
            for vector_name in self.index_metadata["vector_dimensions"]:
                path = self._vector_path(vector_name)
                if path.exists():
                    self.vectors[vector_name] = np.load(path)
        elif self.vectors_path.exists():
            legacy = np.load(self.vectors_path)
            vector_name = f"dense_{legacy.shape[1]}"
            self.vectors[vector_name] = legacy
            self.index_metadata.setdefault("vector_dimensions", {vector_name: int(legacy.shape[1])})
            self.index_metadata.setdefault("default_vector_name", vector_name)

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        _write_json(self.documents_path, [asdict(document) for document in self.documents.values()])
        _write_json(self.metadata_path, [asdict(record) for record in self.records])
        _write_json(self.index_metadata_path, self.index_metadata)
        for vector_name, matrix in self.vectors.items():
            _atomic_save_numpy(self._vector_path(vector_name), matrix)
        if self.default_vector_name and self.default_vector_name in self.vectors:
            _atomic_save_numpy(self.vectors_path, self.vectors[self.default_vector_name])

    def register_embedding_space(
        self,
        *,
        model_name: str,
        backend: str,
        dimensions: dict[str, int],
        default_vector_name: str,
    ) -> None:
        proposed = {
            "schema_version": 3,
            "embedding_model": model_name,
            "embedding_backend": backend,
            "vector_dimensions": dimensions,
            "default_vector_name": default_vector_name,
        }
        if not self.index_metadata:
            self.index_metadata = proposed
            return
        expected = (
            self.index_metadata.get("embedding_model"),
            self.index_metadata.get("embedding_backend"),
            self.index_metadata.get("vector_dimensions"),
            self.index_metadata.get("default_vector_name"),
        )
        actual = (model_name, backend, dimensions, default_vector_name)
        if self.records and expected != actual:
            raise ValueError(
                "Embedding space mismatch: existing index uses "
                f"{expected}, but ingestion produced {actual}. Reindex before mixing embeddings."
            )
        self.index_metadata = proposed

    def upsert_document(
        self,
        document: DocumentManifest,
        records: list[ChunkRecord],
        embeddings: dict[str, np.ndarray],
    ) -> None:
        self._validate_embeddings(records, embeddings)
        self._delete_document_chunks(document.document_id)
        if records:
            for vector_name, matrix in embeddings.items():
                current = self.vectors.get(vector_name)
                if current is None or current.size == 0:
                    self.vectors[vector_name] = matrix.astype(np.float32)
                else:
                    if current.shape[1] != matrix.shape[1]:
                        raise ValueError("Embedding dimension mismatch within the active index.")
                    self.vectors[vector_name] = np.vstack([current, matrix.astype(np.float32)])
            self.records.extend(records)
        self.documents[document.document_id] = document
        self.save()

    def add_records(self, records: list[ChunkRecord], embeddings: np.ndarray) -> None:
        """Backwards-compatible append path for legacy callers."""
        if not records:
            return
        vector_name = self.default_vector_name or f"dense_{embeddings.shape[1]}"
        if vector_name not in self.vectors or self.vectors[vector_name].size == 0:
            self.vectors[vector_name] = embeddings.astype(np.float32)
        else:
            self.vectors[vector_name] = np.vstack([self.vectors[vector_name], embeddings.astype(np.float32)])
        self.records.extend(records)
        self.save()

    def delete_document(self, document_id: str) -> int:
        deleted = self._delete_document_chunks(document_id)
        self.documents.pop(document_id, None)
        self.save()
        return deleted

    def _delete_document_chunks(self, document_id: str) -> int:
        keep_indices = [i for i, record in enumerate(self.records) if record.document_id != document_id]
        deleted = len(self.records) - len(keep_indices)
        self.records = [self.records[i] for i in keep_indices]
        for vector_name, matrix in list(self.vectors.items()):
            dim = matrix.shape[1]
            self.vectors[vector_name] = matrix[keep_indices] if keep_indices else np.empty((0, dim), dtype=np.float32)
        return deleted

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        *,
        vector_name: str | None = None,
        document_ids: set[str] | None = None,
    ) -> list[SearchResult]:
        vector_name = vector_name or self.default_vector_name
        if not vector_name or vector_name not in self.vectors:
            return []
        vectors = self.vectors[vector_name]
        if not self.records or vectors.size == 0:
            return []
        query = query_embedding.reshape(-1)
        if query.shape[0] != vectors.shape[1]:
            raise ValueError(
                f"Query embedding dimension {query.shape[0]} does not match index dimension {vectors.shape[1]}."
            )
        query_norm = np.linalg.norm(query)
        if query_norm:
            query = query / query_norm
        scores = vectors @ query
        candidate_indices = [
            index
            for index, record in enumerate(self.records)
            if document_ids is None or record.document_id in document_ids
        ]
        top_indices = sorted(candidate_indices, key=lambda index: scores[index], reverse=True)[:top_k]
        return [
            SearchResult(record=self.records[int(i)], score=float(max(0.0, min(1.0, scores[int(i)]))))
            for i in top_indices
        ]

    def fetch_vectors(self, chunk_ids: list[str], *, vector_name: str) -> dict[str, np.ndarray]:
        if vector_name not in self.vectors:
            return {}
        requested = set(chunk_ids)
        return {
            record.chunk_id: self.vectors[vector_name][index]
            for index, record in enumerate(self.records)
            if record.chunk_id in requested
        }

    def _vector_path(self, vector_name: str) -> Path:
        return self.index_dir / f"vectors_{vector_name}.npy"

    @staticmethod
    def _validate_embeddings(records: list[ChunkRecord], embeddings: dict[str, np.ndarray]) -> None:
        for vector_name, matrix in embeddings.items():
            if matrix.ndim != 2:
                raise ValueError(f"Embeddings for {vector_name} must be a 2D matrix.")
            if records and len(records) != len(matrix):
                raise ValueError(f"Each chunk must have one embedding in {vector_name}.")


def _document_from_payload(item: dict[str, Any]) -> DocumentManifest:
    payload = dict(item)
    payload.setdefault("status", "indexed")
    payload["warnings"] = tuple(payload.get("warnings", ()))
    payload.setdefault("diagnostics", {})
    payload.setdefault("metadata", {})
    return DocumentManifest(**payload)


def _chunk_from_payload(item: dict[str, Any]) -> ChunkRecord:
    payload = dict(item)
    payload.setdefault("version_id", "legacy")
    payload.setdefault("section_title", None)
    payload["section_path"] = tuple(payload.get("section_path", ()))
    payload.setdefault("page_number", None)
    payload.setdefault("word_count", len(str(payload.get("text", "")).split()))
    payload.setdefault("content_hash", "")
    return ChunkRecord(**payload)


def _reconstruct_documents(records: list[ChunkRecord]) -> dict[str, DocumentManifest]:
    grouped: dict[str, list[ChunkRecord]] = {}
    for record in records:
        grouped.setdefault(record.document_id, []).append(record)
    documents: dict[str, DocumentManifest] = {}
    for document_id, chunks in grouped.items():
        first = chunks[0]
        documents[document_id] = DocumentManifest(
            document_id=document_id,
            source_id=f"legacy:{first.source}",
            version_id=first.version_id,
            content_hash="",
            title=first.title,
            source_type=first.source_type,
            source=first.source,
            original_filename=None,
            chunks_indexed=len(chunks),
            ingested_at="legacy",
            status="indexed",
        )
    return documents


def _write_json(path: Path, payload: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _atomic_save_numpy(path: Path, array: np.ndarray) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("wb") as handle:
        np.save(handle, array)
    tmp_path.replace(path)


class QdrantVectorStore:
    """Qdrant-backed dense vector store with local document-manifest persistence.

    The current project still keeps document manifests on the local filesystem so
    ingestion semantics remain unchanged while vector retrieval migrates to a
    production-grade backend. A future document repository abstraction can move
    manifests into a database/object-store layer without changing retrieval APIs.
    """

    def __init__(self, index_dir: Path, *, url: str, collection_name: str, api_key: str | None = None):
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError("Install qdrant-client to use the qdrant vector-store backend.") from exc

        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.url = url
        self.collection_name = collection_name
        self.client = QdrantClient(url=url, api_key=api_key)
        self.documents: dict[str, DocumentManifest] = {}
        self.index_metadata: dict[str, Any] = {}
        self.load()

    @property
    def documents_path(self) -> Path:
        return self.index_dir / "documents.json"

    @property
    def index_metadata_path(self) -> Path:
        return self.index_dir / "index_metadata.json"

    @property
    def embedding_dimension(self) -> int | None:
        default = self.default_vector_name
        return self.vector_dimensions.get(default) if default else None

    @property
    def vector_dimensions(self) -> dict[str, int]:
        return {
            str(name): int(dimension)
            for name, dimension in self.index_metadata.get("vector_dimensions", {}).items()
        }

    @property
    def default_vector_name(self) -> str | None:
        configured = self.index_metadata.get("default_vector_name")
        if configured:
            return str(configured)
        if self.vector_dimensions:
            return min(self.vector_dimensions, key=self.vector_dimensions.get)
        return None

    @property
    def largest_vector_name(self) -> str | None:
        if self.vector_dimensions:
            return max(self.vector_dimensions, key=self.vector_dimensions.get)
        return None

    @property
    def records(self) -> list[ChunkRecord]:
        # Retained only as a compatibility shim for older call sites. The app now
        # uses count_chunks()/has_records() so Qdrant does not need to eagerly
        # scroll the entire collection during normal operation.
        return []

    def load(self) -> None:
        if self.documents_path.exists():
            raw_documents = json.loads(self.documents_path.read_text(encoding="utf-8"))
            self.documents = {
                item["document_id"]: _document_from_payload(item)
                for item in raw_documents
            }
        if self.index_metadata_path.exists():
            self.index_metadata = json.loads(self.index_metadata_path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        _write_json(self.documents_path, [asdict(document) for document in self.documents.values()])
        _write_json(self.index_metadata_path, self.index_metadata)

    def has_records(self) -> bool:
        return self.count_chunks() > 0

    def count_chunks(self) -> int:
        if not self._collection_exists():
            return 0
        return int(self.client.count(collection_name=self.collection_name, exact=True).count)

    def list_chunks(self) -> list[ChunkRecord]:
        if not self._collection_exists():
            return []
        records: list[ChunkRecord] = []
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            records.extend(
                _chunk_from_payload(point.payload or {})
                for point in points
                if point.payload
            )
            if offset is None:
                break
        return records

    def list_documents(self) -> list[DocumentManifest]:
        return list(self.documents.values())

    def get_document(self, document_id: str) -> DocumentManifest | None:
        return self.documents.get(document_id)

    def register_embedding_space(
        self,
        *,
        model_name: str,
        backend: str,
        dimensions: dict[str, int],
        default_vector_name: str,
    ) -> None:
        proposed = {
            "schema_version": 3,
            "embedding_model": model_name,
            "embedding_backend": backend,
            "vector_dimensions": dimensions,
            "default_vector_name": default_vector_name,
        }
        expected = (
            self.index_metadata.get("embedding_model"),
            self.index_metadata.get("embedding_backend"),
            self.index_metadata.get("vector_dimensions"),
            self.index_metadata.get("default_vector_name"),
        ) if self.index_metadata else None
        actual = (model_name, backend, dimensions, default_vector_name)
        if self.count_chunks() and expected and expected != actual:
            raise ValueError(
                "Embedding space mismatch: existing index uses "
                f"{expected}, but ingestion produced {actual}. Reindex before mixing embeddings."
            )
        self._ensure_collection(dimensions)
        self.index_metadata = proposed
        self.save()

    def upsert_document(
        self,
        document: DocumentManifest,
        records: list[ChunkRecord],
        embeddings: dict[str, np.ndarray],
    ) -> None:
        LocalVectorStore._validate_embeddings(records, embeddings)
        self.delete_document(document.document_id)
        if records:
            from qdrant_client import models

            points = [
                models.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, record.chunk_id)),
                    vector={
                        vector_name: matrix[index].astype(np.float32).tolist()
                        for vector_name, matrix in embeddings.items()
                    },
                    payload=asdict(record),
                )
                for index, record in enumerate(records)
            ]
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
        self.documents[document.document_id] = document
        self.save()

    def delete_document(self, document_id: str) -> int:
        if not self._collection_exists():
            self.documents.pop(document_id, None)
            self.save()
            return 0
        from qdrant_client import models

        selector = models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            )
        )
        deleted = self._count_document_points(document_id)
        self.client.delete(collection_name=self.collection_name, points_selector=selector, wait=True)
        self.documents.pop(document_id, None)
        self.save()
        return deleted

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        *,
        vector_name: str | None = None,
        document_ids: set[str] | None = None,
    ) -> list[SearchResult]:
        if document_ids is not None and not document_ids:
            return []
        if not self._collection_exists() or self.count_chunks() == 0:
            return []
        vector_name = vector_name or self.default_vector_name
        if not vector_name:
            return []
        expected_dimension = self.vector_dimensions.get(vector_name)
        if expected_dimension and query_embedding.reshape(-1).shape[0] != expected_dimension:
            raise ValueError(
                f"Query embedding dimension {query_embedding.reshape(-1).shape[0]} does not match index dimension {expected_dimension}."
            )
        query_filter = None
        if document_ids is not None:
            from qdrant_client import models

            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=list(document_ids)),
                    )
                ]
            )
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.reshape(-1).astype(np.float32).tolist(),
            using=vector_name,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        points = getattr(response, "points", response)
        return [
            SearchResult(record=_chunk_from_payload(point.payload or {}), score=float(max(0.0, min(1.0, point.score))))
            for point in points
        ]

    def fetch_vectors(self, chunk_ids: list[str], *, vector_name: str) -> dict[str, np.ndarray]:
        if not self._collection_exists() or not chunk_ids:
            return {}
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id)) for chunk_id in chunk_ids],
            with_payload=True,
            with_vectors=True,
        )
        vectors: dict[str, np.ndarray] = {}
        for point in points:
            payload = point.payload or {}
            chunk_id = str(payload.get("chunk_id", ""))
            raw_vector = point.vector.get(vector_name) if isinstance(point.vector, dict) else None
            if chunk_id and raw_vector is not None:
                vectors[chunk_id] = np.asarray(raw_vector, dtype=np.float32)
        return vectors

    def _collection_exists(self) -> bool:
        return bool(self.client.collection_exists(collection_name=self.collection_name))

    def _ensure_collection(self, dimensions: dict[str, int]) -> None:
        if self._collection_exists():
            return
        from qdrant_client import models

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                vector_name: models.VectorParams(size=dimension, distance=models.Distance.COSINE)
                for vector_name, dimension in dimensions.items()
            },
        )

    def _count_document_points(self, document_id: str) -> int:
        from qdrant_client import models

        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            ),
            exact=True,
        )
        return int(result.count)


# Backwards-compatible alias while existing imports migrate to the abstraction.
VectorStore = LocalVectorStore
