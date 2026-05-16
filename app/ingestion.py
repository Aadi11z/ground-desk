from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import uuid
from pathlib import Path
import shutil

from .chunking import chunk_sections
from .config import Settings
from .document_loaders import LoadedDocument, LoadedSection, load_path, load_url
from .embeddings import EmbeddingModel
from .ingestion_quality import assess_sections, build_report, filter_chunks
from .models import DocumentRecord
from .vector_store import ChunkRecord, DocumentManifest, VectorStore


class IngestionService:
    def __init__(self, settings: Settings, embeddings: EmbeddingModel, store: VectorStore):
        self.settings = settings
        self.embeddings = embeddings
        self.store = store
        self.settings.documents_dir.mkdir(parents=True, exist_ok=True)

    def ingest_path(
        self,
        path: Path,
        *,
        document_id: str | None = None,
        source_id: str | None = None,
        source: str | None = None,
        title: str | None = None,
        original_filename: str | None = None,
    ) -> DocumentRecord:
        loaded = load_path(
            path,
            source_id=source_id,
            source=source,
            title=title,
            original_filename=original_filename,
        )
        record = self.ingest_loaded(loaded, document_id=document_id)
        target = self.settings.documents_dir / f"{record.document_id}{path.suffix.lower()}"
        if path.resolve() != target.resolve():
            shutil.copy2(path, target)
        return record

    def ingest_url(self, url: str) -> DocumentRecord:
        return self.ingest_loaded(load_url(url))

    def create_uploaded_document(
        self,
        path: Path,
        *,
        original_filename: str,
    ) -> DocumentRecord:
        document_id = _new_document_id()
        return self.ingest_path(
            path,
            document_id=document_id,
            source_id=f"document:{document_id}",
            source=original_filename,
            title=Path(original_filename).stem,
            original_filename=original_filename,
        )

    def replace_uploaded_document(
        self,
        document_id: str,
        path: Path,
        *,
        original_filename: str,
    ) -> DocumentRecord:
        existing = self.store.documents.get(document_id)
        if existing is None:
            raise KeyError(f"Unknown document_id: {document_id}")
        if not existing.source_id.startswith("document:"):
            raise ValueError("Only uploaded documents can be replaced through this endpoint.")
        return self.ingest_path(
            path,
            document_id=document_id,
            source_id=existing.source_id,
            source=original_filename,
            title=Path(original_filename).stem,
            original_filename=original_filename,
        )

    def ingest_loaded(self, loaded: LoadedDocument, *, document_id: str | None = None) -> DocumentRecord:
        source_id = loaded.source_id or f"memory:{loaded.source}"
        content_hash = _sha256(loaded.text)
        document_id = document_id or _document_id(source_id)
        version_id = _version_id(content_hash)
        sections = loaded.sections or (LoadedSection(title=None, text=loaded.text, position=0),)
        usable_sections, quality_warnings, empty_sections = assess_sections(loaded, sections)
        candidate_chunks = chunk_sections(usable_sections, document_id=document_id)
        chunks, chunk_warnings = filter_chunks(candidate_chunks)
        quality_report = build_report(
            warnings=[*quality_warnings, *chunk_warnings],
            total_sections=len(sections),
            indexed_sections=len(usable_sections),
            total_chunks=len(candidate_chunks),
            indexed_chunks=len(chunks),
            empty_sections=empty_sections,
        )
        records = [
            ChunkRecord(
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                version_id=version_id,
                title=loaded.title,
                source_type=loaded.source_type,
                source=loaded.source,
                text=chunk.text,
                position=chunk.position,
                section_title=chunk.section_title,
                section_path=chunk.section_path,
                page_number=chunk.page_number,
                word_count=chunk.word_count,
                content_hash=chunk.content_hash,
            )
            for chunk in chunks
        ]
        vectors = self.embeddings.encode([record.text for record in records])
        embedding_dimension = vectors.shape[1] if vectors.ndim == 2 and vectors.size else self.store.embeddings.shape[1]
        self.store.register_embedding_space(
            model_name=self.embeddings.model_name,
            backend=self.embeddings.backend,
            dimension=embedding_dimension,
        )
        manifest = DocumentManifest(
            document_id=document_id,
            source_id=source_id,
            version_id=version_id,
            content_hash=content_hash,
            title=loaded.title,
            source_type=loaded.source_type,
            source=loaded.source,
            original_filename=loaded.original_filename,
            chunks_indexed=len(records),
            ingested_at=datetime.now(timezone.utc).isoformat(),
            status="rejected" if quality_report.rejected else ("indexed_with_warnings" if quality_report.warnings else "indexed"),
            warnings=quality_report.warnings,
            diagnostics={
                "total_sections": quality_report.total_sections,
                "indexed_sections": quality_report.indexed_sections,
                "empty_sections": quality_report.empty_sections,
                "total_chunks": quality_report.total_chunks,
                "indexed_chunks": quality_report.indexed_chunks,
                "skipped_chunks": quality_report.skipped_chunks,
            },
            metadata=loaded.metadata,
        )
        self.store.upsert_document(manifest, records, vectors)
        return _document_record(manifest)

    def ingest_sample_corpus(self) -> list[DocumentRecord]:
        if not self.settings.sample_dir.exists():
            return []
        records = []
        for path in sorted(self.settings.sample_dir.glob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".pdf"}:
                records.append(self.ingest_path(path))
        return records

    def list_documents(self) -> list[DocumentRecord]:
        return [
            _document_record(document)
            for document in sorted(self.store.documents.values(), key=lambda item: item.title.lower())
        ]


def _document_record(manifest: DocumentManifest) -> DocumentRecord:
    return DocumentRecord(
        document_id=manifest.document_id,
        source_id=manifest.source_id,
        version_id=manifest.version_id,
        content_hash=manifest.content_hash,
        title=manifest.title,
        source_type=manifest.source_type,
        source=manifest.source,
        original_filename=manifest.original_filename,
        chunks_indexed=manifest.chunks_indexed,
        ingested_at=manifest.ingested_at,
        status=manifest.status,
        warnings=list(manifest.warnings),
        diagnostics=manifest.diagnostics,
    )


def _document_id(source_id: str) -> str:
    return f"doc_{_sha256(source_id)[:12]}"


def _new_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def _version_id(content_hash: str) -> str:
    return f"ver_{content_hash[:12]}"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
