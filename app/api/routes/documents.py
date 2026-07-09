from fastapi import APIRouter, Depends, HTTPException, Header, File, UploadFile
from app.api.dependencies import get_ingestion_service, get_vector_store, normal_access_context, require_admin
from app.core.auth import AccessContext
from app.core.models import DocumentIngestResponse
from app.core.workspace import normalize_workspace_id
from app.core.config import settings

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)


@router.get("")
def list_docs(
    context: AccessContext = Depends(normal_access_context),
    ingestion_service = Depends(get_ingestion_service)
):
    return ingestion_service.list_documents(
        metadata_filter={"workspace_id": context.workspace_id}
    )

def workspace_id_from_header(value: str | None) -> str:
    try:
        return normalize_workspace_id(value, default=settings.default_workspace_id)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex)) from ex

def ensure_workspace_document(document_id: str, workspace_id: str, store):
    document = store.get_document(document_id)
    if document is None or not metadata_matches_workspace(
        document.metadata,
        workspace_id,
        default=settings.default_workspace_id
    ):
        raise HTTPException(status_code=404, detail=f"Unknown document_id: {document_id}")
    
    return document
    
@router.post("", response_model=DocumentIngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    ingestion_service=Depends(get_ingestion_service),
):
    workspace_id = workspace_id_from_header(x_workspace_id)

    suffix = Path(file.filename or "document.txt").suffix

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        original_filename = file.filename or "document.txt"
        record = ingestion_service.create_uploaded_document(
            tmp_path,
            original_filename=original_filename,
            metadata={"workspace_id": workspace_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return DocumentIngestResponse(
        document_id=record.document_id,
        status=record.status,
        chunks_indexed=record.chunks_indexed,
        warnings=record.warnings,
    )