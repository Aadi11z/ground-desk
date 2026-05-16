from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
from .chunking import chunk_text
from .config import Settings
from .document_loaders import LoadedDocument, load_path, load_url
from .embeddings import EmbeddingModel
from .models import DocumentRecord
from .safety import strip_prompt_injection
from .vector_store import ChunkRecord, VectorStore


class IngestionService:
    def __init__(self, settings: Settings, embeddings: EmbeddingModel, store: VectorStore):
        self.settings = settings
        self.embeddings = embeddings
        self.store = store
        self.settings.documents_dir.mkdir(parents=True, exist_ok=True)

    def ingest_path(self, path: Path) -> DocumentRecord:
        loaded = load_path(path)
        target = self.settings.documents_dir / path.name
        if path.resolve() != target.resolve():
            shutil.copy2(path, target)
        return self.ingest_loaded(loaded)

    def ingest_url(self, url: str) -> DocumentRecord:
        return self.ingest_loaded(load_url(url))

    def ingest_loaded(self, loaded: LoadedDocument) -> DocumentRecord:
        normalized_text = strip_prompt_injection(loaded.text)
        document_id = _document_id(loaded.source, normalized_text)
        self.store.delete_document(document_id)

        chunks = chunk_text(normalized_text, document_id=document_id)
        records = [
            ChunkRecord(
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                title=loaded.title,
                source_type=loaded.source_type,
                source=loaded.source,
                text=chunk.text,
                position=chunk.position,
            )
            for chunk in chunks
        ]
        vectors = self.embeddings.encode([record.text for record in records])
        self.store.add_records(records, vectors)
        return DocumentRecord(
            document_id=document_id,
            title=loaded.title,
            source_type=loaded.source_type,
            source=loaded.source,
            chunks_indexed=len(records),
        )

    def ingest_sample_corpus(self) -> list[DocumentRecord]:
        if not self.settings.sample_dir.exists():
            return []
        records = []
        for path in sorted(self.settings.sample_dir.glob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".pdf"}:
                records.append(self.ingest_path(path))
        return records

    def list_documents(self) -> list[DocumentRecord]:
        grouped: dict[str, list[ChunkRecord]] = {}
        for record in self.store.records:
            grouped.setdefault(record.document_id, []).append(record)
        documents = []
        for document_id, chunks in sorted(grouped.items()):
            first = chunks[0]
            documents.append(
                DocumentRecord(
                    document_id=document_id,
                    title=first.title,
                    source_type=first.source_type,
                    source=first.source,
                    chunks_indexed=len(chunks),
                )
            )
        return documents


def _document_id(source: str, text: str) -> str:
    digest = hashlib.sha1(f"{source}\n{text}".encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"

