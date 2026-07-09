from fastapi import APIRouter, Depends, HTTPException, Header, File, UploadFile
from app.api.dependencies import get_ingestion_service, get_vector_store, normal_access_context, require_admin
from app.core.auth import AccessContext
from app.core.models import DocumentIngestResponse

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

@router.post("", response_model=DocumentIngestResponse)
async def upload_docs(
    file: UploadFile = File(...),
    _: None = Depends(require_admin),
    workspace_id: str | None = Header(default=None, alias="X-Workspace-ID")
) -> DocumentIngestResponse:
    workspace_id = workspace_id()