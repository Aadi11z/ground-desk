import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import (
    _document_text,
    _ensure_workspace_document,
    get_ingestion_service,
    get_vector_store,
    require_document_manager,
    require_document_reader,
)
from app.core.auth import AccessContext
from app.core.models import DocumentIngestResponse, DocumentPreview, UrlIngestRequest

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(
    context: AccessContext = Depends(require_document_reader),
    ingestion_service=Depends(get_ingestion_service),
):
    return ingestion_service.list_documents(
        context, metadata_filter={"workspace_id": context.workspace_id}
    )


@router.get("/{document_id}/preview", response_model=DocumentPreview)
def preview_document(
    document_id: str,
    context: AccessContext = Depends(require_document_reader),
    store=Depends(get_vector_store),
) -> DocumentPreview:
    """Return an authorized extracted-text preview without exposing storage paths."""
    document = _ensure_workspace_document(document_id, context, store=store)
    text = _document_text(document_id, context, store=store)
    limit = 100_000
    return DocumentPreview(
        document_id=document.document_id,
        title=document.title,
        original_filename=document.original_filename,
        text=text[:limit],
        truncated=len(text) > limit,
    )


def _response(record) -> DocumentIngestResponse:
    return DocumentIngestResponse(
        document_id=record.document_id,
        status=record.status,
        chunks_indexed=record.chunks_indexed,
        warnings=record.warnings,
    )


@router.post("", response_model=DocumentIngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    context: AccessContext = Depends(require_document_manager),
    ingestion_service=Depends(get_ingestion_service),
) -> DocumentIngestResponse:
    suffix = Path(file.filename or "document.txt").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        record = ingestion_service.create_uploaded_document(
            context,
            tmp_path,
            original_filename=file.filename or "document.txt",
            metadata={"workspace_id": context.workspace_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return _response(record)


@router.put("/{document_id}", response_model=DocumentIngestResponse)
async def replace_document(
    document_id: str,
    file: UploadFile = File(...),
    context: AccessContext = Depends(require_document_manager),
    ingestion_service=Depends(get_ingestion_service),
    store=Depends(get_vector_store),
) -> DocumentIngestResponse:
    _ensure_workspace_document(document_id, context, store=store)
    suffix = Path(file.filename or "document.txt").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        record = ingestion_service.replace_uploaded_document(
            context,
            document_id,
            tmp_path,
            original_filename=file.filename or "document.txt",
            metadata={"workspace_id": context.workspace_id},
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return _response(record)


@router.post("/url", response_model=DocumentIngestResponse)
def ingest_url(
    request: UrlIngestRequest,
    context: AccessContext = Depends(require_document_manager),
    ingestion_service=Depends(get_ingestion_service),
) -> DocumentIngestResponse:
    try:
        record = ingestion_service.ingest_url(
            context, request.url, metadata={"workspace_id": context.workspace_id}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(record)


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    context: AccessContext = Depends(require_document_manager),
    store=Depends(get_vector_store),
):
    _ensure_workspace_document(document_id, context, store=store)
    return {
        "document_id": document_id,
        "chunks_deleted": store.delete_document(context, document_id),
    }
