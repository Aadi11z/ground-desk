"""Public process probes."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_app_settings
from app.core.models import HealthResponse
from app.infrastructure.config import Settings

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "Page not found!"}},
)


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
