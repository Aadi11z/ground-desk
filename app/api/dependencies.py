from pydantic import computed_field
from app.core.config import settings
from app.rag.ingestion.service import IngestionService
from app.rag.retrieval.embeddings import EmbeddingModel
from app.rag.retrieval.factory import create_vector_store
from app.rag.generation.agent import SupportAgent
from app.rag.generation.workflows import SupportWorkflowService
from app.core.persistence import create_product_repository
from app.core.auth import AccessController

embedding_model = EmbeddingModel(
    settings.embedding_model,
    provider=settings.embedding_provider,
    mrl_dimensions=settings.embedding_dimensions,
    max_attempts=settings.gemini_embedding_max_attempts,
    retry_base_seconds=settings.gemini_embedding_retry_base_seconds
)
vector_store = create_vector_store(settings)
ingestion_service = IngestionService(settings, embedding_model, vector_store)
agent = SupportAgent(settings, embedding_model, vector_store)
workflows = SupportWorkflowService(agent)
product_repository = create_product_repository(settings)
access_controller = AccessController(settings, product_repository)

def require_admin(
    x_admin_api_key: str | None = Header(default=None, alias="X-Admin-API-Key"),
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=404,detail="Management endpoints are disabled")
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid admin API key.")

def _workspace_id(value: str | None) -> str:
    try:
        return normalize_workspace_id(value, default=settings.default_workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def normal_access_context(authorization: str | None = Header(default=None, alias="Authorization"),x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID")) -> AccessContext:
    try:
        return access_controller.resolve(
            authorization=authorization,
            requested_workspace_id=x_workspace_id,
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def authenticated_access_context(authorization: str | None = Header(default=None, alias="Authorization"),x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID")) -> AccessContext:
    try:
        return access_controller.resolve(
            authorization=authorization,
            requested_workspace_id=x_workspace_id,
            require_authenticated=True,
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _ensure_workspace_document(document_id: str, workspace_id: str):
    document = vector_store.get_document(document_id)
    if document is None or not metadata_matches_workspace(
        document.metadata,
        workspace_id,
        default=settings.default_workspace_id,
    ):
        raise HTTPException(
            status_code=404, detail=f"Unknown document_id: {document_id}"
        )
    return document

def _document_text(document_id: str) -> str:
    return "\n\n".join(
        record.text
        for record in vector_store.list_chunks()
        if record.document_id == document_id
    )
    
# Getters
def get_vector_store():
    return vector_store

def get_ingestion_service():
    return ingestion_service

def get_agent():
    return agent

def get_product_repository():
    return product_repository

def get_access_controller():
    return access_controller
