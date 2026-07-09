from fastapi import APIRouter, HTTPException, Depends
from app.api.dependencies import (
    get_vector_store,
    get_product_repository,
    get_access_controller,
)
from app.core.config import settings
from app.core.models import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "Page not found!"}},
)


@router.get("", response_model=HealthResponse)
async def health(
    store: Depends(get_vector_store),
    repository=Depends(get_product_repository),
    access_controller=Depends(get_access_controller)
) -> HealthResponse:
    health_error = None
    
    try:
        chunks = store.count_chunks()
        repository.healthcheck()
        access_controller.healthcheck_configuration()
    except Exception as ex:
        chunks = 0
        health_error = str(ex)
        
    return HealthResponse(
        app=settings.app_name,
        status="degraded" if health_error else "ok",
        documents=0,
        chunks=chunks,
        embedding_model=settings.embedding_model,
        startup_error=health_error
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
        store.count_chunk()
        repository.healthcheck()
        access_controller.healthcheck_configuration()
    except:
        raise HTTPException(status_code=503, detail="Service is not ready")

    return {"status": "ok"}
