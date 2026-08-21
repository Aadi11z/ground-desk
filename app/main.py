"""Canonical ASGI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router as api_router
from app.api.routes.health import router as health_router
from app.bootstrap import build_services
from app.infrastructure.config import Settings, get_settings


def create_app(config: Settings | None = None) -> FastAPI:
    """Create an application with services owned by its lifespan."""
    settings = config or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        services = build_services(settings)
        app.state.settings = settings
        app.state.services = services
        try:
            yield
        finally:
            _close_services(services)

    app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
    app.include_router(api_router)
    app.include_router(health_router)
    return app


app = create_app()


def _close_services(services) -> None:
    """Release optional adapters in the reverse order of their use."""
    close_vector_store = getattr(services.vector_store, "close", None)
    if callable(close_vector_store):
        close_vector_store()
    if services.database_runtime is not None:
        services.database_runtime.close()
