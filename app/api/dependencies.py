from fastapi import Depends, Header, HTTPException, Request

from app.bootstrap import AppServices
from app.core.auth import (
    AccessContext,
    AccessController,
    AccessError,
    AuthenticatedUser,
)
from app.core.workspace import normalize_workspace_id
from app.domain.permissions import Permission
from app.infrastructure.config import Settings
from app.infrastructure.config import settings as compatibility_settings


def get_services(request: Request) -> AppServices:
    """Resolve lifespan-owned services for the current application instance."""
    try:
        return request.app.state.services
    except AttributeError as exc:
        raise RuntimeError("GroundDesk services are not initialized.") from exc


def get_app_settings(request: Request) -> Settings:
    try:
        return request.app.state.settings
    except AttributeError as exc:
        raise RuntimeError("GroundDesk settings are not initialized.") from exc


def get_database_session(request: Request):
    runtime = get_services(request).database_runtime
    if runtime is None:
        yield None
        return
    with runtime.session() as session:
        yield session


def get_product_repository(
    request: Request,
    session=Depends(get_database_session),
):
    repository = get_services(request).product_repository
    return repository.bind_session(session) if session is not None else repository


def require_admin(
    request: Request,
    x_admin_api_key: str | None = Header(default=None, alias="X-Admin-API-Key"),
) -> None:
    admin_api_key = get_app_settings(request).admin_api_key_value
    if not admin_api_key:
        raise HTTPException(status_code=404, detail="Management endpoints are disabled")
    if x_admin_api_key != admin_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid admin API key.")


def _workspace_id(value: str | None) -> str:
    try:
        return normalize_workspace_id(
            value, default=compatibility_settings.default_workspace_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def normal_access_context(
    request: Request,
    repository=Depends(get_product_repository),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> AccessContext:
    try:
        controller = get_services(request).access_controller
        request_controller = AccessController(
            get_app_settings(request), repository, verifier=controller.verifier
        )
        return request_controller.resolve(
            authorization=authorization,
            requested_workspace_id=x_workspace_id,
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def authenticated_access_context(
    request: Request,
    repository=Depends(get_product_repository),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> AccessContext:
    try:
        controller = get_services(request).access_controller
        request_controller = AccessController(
            get_app_settings(request), repository, verifier=controller.verifier
        )
        return request_controller.resolve(
            authorization=authorization,
            requested_workspace_id=x_workspace_id,
            require_authenticated=True,
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def authenticated_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    try:
        return get_services(request).access_controller.authenticate(authorization)
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _require_permission(
    context: AccessContext, permission: Permission
) -> AccessContext:
    if not context.allows(permission):
        raise HTTPException(status_code=403, detail="Permission denied.")
    return context


def require_document_reader(
    context: AccessContext = Depends(normal_access_context),
) -> AccessContext:
    return _require_permission(context, Permission.DOCUMENTS_READ)


def require_document_manager(
    context: AccessContext = Depends(normal_access_context),
) -> AccessContext:
    return _require_permission(context, Permission.DOCUMENTS_WRITE)


def _ensure_workspace_document(document_id: str, context: AccessContext, *, store):
    document = store.get_document(context, document_id)
    if document is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown document_id: {document_id}"
        )
    return document


def _document_text(document_id: str, context: AccessContext, *, store) -> str:
    return "\n\n".join(
        record.text
        for record in sorted(
            store.list_chunks(context),
            key=lambda record: (record.position, record.chunk_id),
        )
        if record.document_id == document_id
    )


def get_vector_store(request: Request):
    return get_services(request).vector_store


def get_embedding_model(request: Request):
    return get_services(request).embedding_model


def get_ingestion_service(request: Request):
    return get_services(request).ingestion_service


def get_agent(request: Request):
    return get_services(request).agent


def get_workflows(request: Request):
    return get_services(request).workflows


def get_access_controller(request: Request):
    return get_services(request).access_controller
