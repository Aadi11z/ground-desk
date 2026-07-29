from __future__ import annotations

from app.core.config import Settings

from .vector_store import LocalVectorStore, QdrantVectorStore, VectorStoreBackend


def create_vector_store(settings: Settings) -> VectorStoreBackend:
    backend = settings.vector_store_backend.lower()
    if backend == "local":
        return LocalVectorStore(settings.index_dir)
    if backend == "qdrant":
        return QdrantVectorStore(
            settings.index_dir,
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection,
        )
    raise ValueError(
        f"Unsupported vector-store backend: {settings.vector_store_backend}"
    )
