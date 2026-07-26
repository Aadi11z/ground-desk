from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_access_controller,
    get_product_repository,
    get_vector_store,
)
from app.core.config import settings
from app.core.models import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "Page not found!"}},
)


@router.get("", response_model=HealthResponse)
def health(
    store=Depends(get_vector_store),
    repository=Depends(get_product_repository),
    access_controller=Depends(get_access_controller),
) -> HealthResponse:
    try:
        chunks = store.count_chunks()
        repository.healthcheck()
        access_controller.healthcheck_configuration()
    except Exception as exc:
        return HealthResponse(
            app=settings.app_name,
            status="degraded",
            documents=0,
            chunks=0,
            embedding_model=settings.embedding_model,
            startup_error=str(exc),
        )
    return HealthResponse(
        app=settings.app_name,
        status="ok",
        documents=len(store.list_documents()),
        chunks=chunks,
        embedding_model=settings.embedding_model,
    )


@router.get("/live")
def live():
    return {"status": "ok"}


@router.get("/ready")
def ready(
    store=Depends(get_vector_store),
    repository=Depends(get_product_repository),
    access_controller=Depends(get_access_controller),
):
    try:
        store.count_chunks()
        repository.healthcheck()
        access_controller.healthcheck_configuration()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Service is not ready") from exc
    return {"status": "ok"}
