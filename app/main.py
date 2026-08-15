"""Canonical ASGI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router as api_router
from app.api.routes.health import internal_router
from app.api.routes.health import router as health_router
from app.bootstrap import build_services
from app.domain.permissions import WorkspaceRole
from app.domain.tenancy import TenantScope
from app.infrastructure.config import Settings, get_settings

WEB_DIR = Path(__file__).with_name("web")


def create_app(config: Settings | None = None) -> FastAPI:
    """Create an application with services owned by its lifespan."""
    settings = config or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        services = build_services(settings)
        app.state.settings = settings
        app.state.services = services
        if settings.auth_mode == "demo" and settings.demo_bootstrap_sample_corpus:
            demo_scope = TenantScope(
                workspace_id=settings.default_workspace_id,
                user_id=settings.demo_user_id,
                role=WorkspaceRole.OWNER,
            )
            if not services.vector_store.has_records(
                demo_scope
            ) or not services.ingestion_service.list_documents(
                demo_scope,
                metadata_filter={"workspace_id": settings.default_workspace_id},
            ):
                services.ingestion_service.ingest_sample_corpus(
                    demo_scope, metadata={"workspace_id": settings.default_workspace_id}
                )
        try:
            yield
        finally:
            close = getattr(services.vector_store, "close", None)
            if callable(close):
                close()
            if services.database_runtime is not None:
                services.database_runtime.close()

    app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
    app.mount("/assets", StaticFiles(directory=WEB_DIR), name="web-assets")

    @app.get("/", include_in_schema=False)
    def product_interface() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.include_router(api_router)
    app.include_router(health_router)
    app.include_router(internal_router)
    return app


app = create_app()
