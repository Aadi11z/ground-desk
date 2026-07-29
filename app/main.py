from fastapi import FastAPI

from app.api.dependencies import get_ingestion_service, get_vector_store
from app.api.router import router as api_router
from app.api.routes.demo import router as demo_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.2.0")
app.include_router(api_router)
app.include_router(demo_router)


@app.on_event("startup")
def startup() -> None:
    """Keep local demo bootstrapping behavior during the API migration."""
    if settings.auth_mode.lower() != "demo":
        return
    vector_store = get_vector_store()
    ingestion_service = get_ingestion_service()
    if not vector_store.has_records() or not ingestion_service.list_documents(
        metadata_filter={"workspace_id": settings.default_workspace_id}
    ):
        ingestion_service.ingest_sample_corpus(
            metadata={"workspace_id": settings.default_workspace_id}
        )
