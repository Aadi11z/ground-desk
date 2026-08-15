"""Public process probes and private dependency diagnostics."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_access_controller,
    get_app_settings,
    get_product_repository,
    get_vector_store,
    require_admin,
)
from app.core.models import HealthResponse
from app.infrastructure.config import Settings

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "Page not found!"}},
)
internal_router = APIRouter(prefix="/internal/health", tags=["internal-health"])


@router.get("", response_model=HealthResponse)
def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Compatibility status endpoint without dependency probes or data counts."""
    return HealthResponse(
        app=settings.app_name,
        status="ok",
        documents=0,
        chunks=0,
        embedding_model=settings.embedding_model,
    )


@router.get("/live")
def live():
    """Report only whether the ASGI process can answer a request."""
    return {"status": "ok"}


@router.get("/ready")
def ready(settings: Settings = Depends(get_app_settings)):
    """Report validated startup and initialized application state.

    This deliberately does not count documents or make database, vector, model,
    or storage calls. Platform probes therefore cannot create provider traffic.
    """
    return {"status": "ok", "environment": settings.app_environment}


@internal_router.get("/dependencies", dependencies=[Depends(require_admin)])
def dependency_diagnostics(
    store=Depends(get_vector_store),
    repository=Depends(get_product_repository),
    access_controller=Depends(get_access_controller),
):
    """Perform bounded, authenticated checks without exposing error details."""
    try:
        # Do not aggregate tenant-owned data in a process diagnostic.
        _ = store.embedding_dimension
        repository.healthcheck()
        access_controller.healthcheck_configuration()
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Dependencies are unavailable."
        ) from exc
    return {"status": "ok"}
