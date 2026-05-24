"""Copy the current local dense index into a configured Qdrant collection."""

from __future__ import annotations

from collections import defaultdict

from app.core.config import settings
from app.retrieval.vector_store import LocalVectorStore, QdrantVectorStore


def main() -> None:
    local_store = LocalVectorStore(settings.index_dir)
    if not local_store.has_records():
        raise SystemExit("Local vector store is empty; nothing to migrate.")
    if not local_store.index_metadata:
        raise SystemExit(
            "Local vector store has no embedding metadata; reindex locally before migration."
        )

    qdrant_store = QdrantVectorStore(
        settings.index_dir,
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection,
    )
    qdrant_store.register_embedding_space(
        model_name=str(local_store.index_metadata["embedding_model"]),
        backend=str(local_store.index_metadata["embedding_backend"]),
        dimensions=local_store.vector_dimensions,
        default_vector_name=str(local_store.default_vector_name),
    )

    records_by_document: dict[str, list[tuple[int, object]]] = defaultdict(list)
    for index, record in enumerate(local_store.records):
        records_by_document[record.document_id].append((index, record))

    migrated = 0
    for document in local_store.list_documents():
        indexed_records = records_by_document.get(document.document_id, [])
        indices = [index for index, _ in indexed_records]
        records = [record for _, record in indexed_records]
        embeddings = {
            vector_name: matrix[indices] if indices else matrix[:0]
            for vector_name, matrix in local_store.vectors.items()
        }
        qdrant_store.upsert_document(document, records, embeddings)
        migrated += 1

    print(
        f"Migrated {migrated} documents and {local_store.count_chunks()} chunks "
        f"to Qdrant collection '{settings.qdrant_collection}'."
    )


if __name__ == "__main__":
    main()
