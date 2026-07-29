import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.api.dependencies import (
    _ensure_workspace_document,
    _workspace_id,
    get_ingestion_service,
    get_vector_store,
    normal_access_context,
    require_admin,
)
from app.core.auth import AccessContext
from app.core.config import settings
from app.core.models import DocumentIngestResponse, UrlIngestRequest
from app.core.workspace import normalize_workspace_id

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(
    context: AccessContext = Depends(normal_access_context),
    ingestion_service=Depends(get_ingestion_service),
):
    return ingestion_service.list_documents(
        metadata_filter={"workspace_id": context.workspace_id}
    )


def _workspace_id_from_header(value: str | None) -> str:
    try:
        return normalize_workspace_id(value, default=settings.default_workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    ingestion_service=Depends(get_ingestion_service),
) -> DocumentIngestResponse:
    workspace_id = _workspace_id_from_header(x_workspace_id)
    suffix = Path(file.filename or "document.txt").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        record = ingestion_service.create_uploaded_document(
            tmp_path,
            original_filename=file.filename or "document.txt",
            metadata={"workspace_id": workspace_id},
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
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    ingestion_service=Depends(get_ingestion_service),
    store=Depends(get_vector_store),
) -> DocumentIngestResponse:
    workspace_id = _workspace_id(x_workspace_id)
    _ensure_workspace_document(document_id, workspace_id, store=store)
    suffix = Path(file.filename or "document.txt").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        record = ingestion_service.replace_uploaded_document(
            document_id,
            tmp_path,
            original_filename=file.filename or "document.txt",
            metadata={"workspace_id": workspace_id},
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
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    ingestion_service=Depends(get_ingestion_service),
) -> DocumentIngestResponse:
    workspace_id = _workspace_id(x_workspace_id)
    try:
        record = ingestion_service.ingest_url(
            request.url, metadata={"workspace_id": workspace_id}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(record)


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    store=Depends(get_vector_store),
):
    workspace_id = _workspace_id(x_workspace_id)
    _ensure_workspace_document(document_id, workspace_id, store=store)
    return {
        "document_id": document_id,
        "chunks_deleted": store.delete_document(document_id),
    }
