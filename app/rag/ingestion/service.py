from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.core.models import DocumentRecord
from app.domain.tenancy import TenantScope
from app.rag.retrieval.embeddings import EmbeddingModel
from app.rag.retrieval.vector_store import (
    ChunkRecord,
    DocumentManifest,
    VectorStoreBackend,
)

from .chunking import chunk_sections
from .loaders import LoadedDocument, LoadedSection, load_path
from .quality import assess_sections, build_report, filter_chunks
from .storage import LocalObjectStore


class IngestionService:
    def __init__(
        self, settings: Settings, embeddings: EmbeddingModel, store: VectorStoreBackend
    ):
        self.settings = settings
        self.embeddings = embeddings
        self.store = store
        self.settings.documents_dir.mkdir(parents=True, exist_ok=True)
        self.object_store = LocalObjectStore(self.settings.documents_dir)

    def ingest_path(
        self,
        scope: TenantScope,
        path: Path,
        *,
        document_id: str | None = None,
        source_id: str | None = None,
        source: str | None = None,
        title: str | None = None,
        original_filename: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> DocumentRecord:
        loaded = load_path(
            path,
            source_id=source_id,
            source=source,
            title=title,
            original_filename=original_filename,
        )
        loaded = _with_metadata(loaded, _scoped_metadata(scope, metadata))
        record = self.ingest_loaded(scope, loaded, document_id=document_id)
        self.object_store.put(path, key=f"{record.document_id}{path.suffix.lower()}")
        return record

    def create_uploaded_document(
        self,
        scope: TenantScope,
        path: Path,
        *,
        original_filename: str,
        metadata: dict[str, str] | None = None,
    ) -> DocumentRecord:
        document_id = _new_document_id()
        return self.ingest_path(
            scope,
            path,
            document_id=document_id,
            source_id=f"document:{document_id}",
            source=original_filename,
            title=Path(original_filename).stem,
            original_filename=original_filename,
            metadata=metadata,
        )

    def replace_uploaded_document(
        self,
        scope: TenantScope,
        document_id: str,
        path: Path,
        *,
        original_filename: str,
        metadata: dict[str, str] | None = None,
    ) -> DocumentRecord:
        existing = self.store.get_document(scope, document_id)
        if existing is None:
            raise KeyError(f"Unknown document_id: {document_id}")
        if not existing.source_id.startswith("document:"):
            raise ValueError(
                "Only uploaded documents can be replaced through this endpoint."
            )
        replacement_metadata = dict(existing.metadata)
        replacement_metadata.update(metadata or {})
        return self.ingest_path(
            scope,
            path,
            document_id=document_id,
            source_id=existing.source_id,
            source=original_filename,
            title=Path(original_filename).stem,
            original_filename=original_filename,
            metadata=replacement_metadata,
        )

    def ingest_loaded(
        self,
        scope: TenantScope,
        loaded: LoadedDocument,
        *,
        document_id: str | None = None,
    ) -> DocumentRecord:
        loaded = _with_metadata(loaded, _scoped_metadata(scope, loaded.metadata))
        source_id = loaded.source_id or f"memory:{loaded.source}"
        content_hash = _sha256(loaded.text)
        document_id = document_id or _document_id(scope.workspace_id, source_id)
        version_id = _version_id(content_hash)
        sections = loaded.sections or (
            LoadedSection(title=None, text=loaded.text, position=0),
        )
        usable_sections, quality_warnings, empty_sections = assess_sections(
            loaded, sections
        )
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
                workspace_id=scope.workspace_id,
            )
            for chunk in chunks
        ]
        vector_batch = self.embeddings.encode_documents(
            [record.text for record in records],
            titles=[record.title for record in records],
        )
        self.store.register_embedding_space(
            model_name=self.embeddings.model_name,
            backend=self.embeddings.backend,
            dimensions=vector_batch.dimensions,
            default_vector_name=vector_batch.default_name,
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
            ingested_at=datetime.now(UTC).isoformat(),
            status="rejected"
            if quality_report.rejected
            else ("indexed_with_warnings" if quality_report.warnings else "indexed"),
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
            workspace_id=scope.workspace_id,
        )
        self.store.upsert_document(scope, manifest, records, vector_batch.vectors)
        return _document_record(manifest)

    def ingest_trial_corpus(
        self, scope: TenantScope, *, metadata: dict[str, str] | None = None
    ) -> list[DocumentRecord]:
        if not self.settings.corpus_dir.exists():
            return []
        records = []
        for path in sorted(self.settings.corpus_dir.glob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".pdf"}:
                records.append(self.ingest_path(scope, path, metadata=metadata))
        return records

    def list_documents(
        self,
        scope: TenantScope,
        *,
        metadata_filter: dict[str, str] | None = None,
    ) -> list[DocumentRecord]:
        documents = self.store.list_documents(scope)
        if metadata_filter:
            documents = [
                document
                for document in documents
                if _metadata_matches_filter(
                    document.metadata,
                    metadata_filter,
                    default_workspace_id=scope.workspace_id,
                )
            ]
        return [
            _document_record(document)
            for document in sorted(documents, key=lambda item: item.title.lower())
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
        metadata=manifest.metadata,
    )


def _with_metadata(
    loaded: LoadedDocument, metadata: dict[str, str] | None
) -> LoadedDocument:
    if not metadata:
        return loaded
    merged = dict(loaded.metadata)
    merged.update({str(key): str(value) for key, value in metadata.items()})
    return LoadedDocument(
        title=loaded.title,
        text=loaded.text,
        source_type=loaded.source_type,
        source=loaded.source,
        source_id=loaded.source_id,
        original_filename=loaded.original_filename,
        sections=loaded.sections,
        metadata=merged,
    )


def _scoped_metadata(
    scope: TenantScope, metadata: dict[str, str] | None
) -> dict[str, str]:
    merged = {str(key): str(value) for key, value in (metadata or {}).items()}
    requested_workspace_id = merged.get("workspace_id")
    if requested_workspace_id not in (None, scope.workspace_id):
        raise ValueError("Document workspace does not match the tenant scope.")
    merged["workspace_id"] = scope.workspace_id
    return merged


def _metadata_matches_filter(
    metadata: dict[str, str], filters: dict[str, str], *, default_workspace_id: str
) -> bool:
    for key, expected in filters.items():
        actual = metadata.get(key)
        if key == "workspace_id":
            actual = actual or default_workspace_id
        if actual != expected:
            return False
    return True


def _document_id(workspace_id: str, source_id: str) -> str:
    return f"doc_{_sha256(f'{workspace_id}:{source_id}')[:12]}"


def _new_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def _version_id(content_hash: str) -> str:
    return f"ver_{content_hash[:12]}"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
