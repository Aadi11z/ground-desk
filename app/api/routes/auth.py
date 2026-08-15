"""Browser session and workspace-onboarding endpoints.

Supabase owns account creation and password handling. This router only exposes
the local demo session and creates GroundDesk tenancy records after an
authenticated Supabase user has signed in.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    authenticated_user,
    get_app_settings,
    get_product_repository,
)
from app.core.auth import AuthenticatedUser
from app.core.models import WorkspaceOnboardingRequest
from app.infrastructure.config import Settings

router = APIRouter(tags=["authentication"])


@router.post("/auth/demo-session")
def create_demo_session(settings: Settings = Depends(get_app_settings)):
    """Return the fixed local-demo identity; unavailable outside demo mode."""
    if settings.auth_mode != "demo":
        raise HTTPException(status_code=404, detail="Demo sign-in is unavailable.")
    return {
        "access_token": "grounddesk-demo-session",
        "user": {
            "id": settings.demo_user_id,
            "email": settings.demo_user_email,
            "display_name": settings.demo_user_name,
        },
        "workspace": {
            "id": settings.default_workspace_id,
            "name": "Demo Workspace",
        },
    }


@router.get("/me")
def me(
    user: AuthenticatedUser = Depends(authenticated_user),
    repository=Depends(get_product_repository),
):
    profile = repository.get_profile(user.user_id) or {
        "user_id": user.user_id,
        "email": user.email,
        "display_name": user.display_name,
    }
    return {
        "user": profile,
        "workspaces": repository.list_user_workspaces(user.user_id),
    }


@router.post("/onboarding")
def create_workspace(
    request: WorkspaceOnboardingRequest,
    user: AuthenticatedUser = Depends(authenticated_user),
    repository=Depends(get_product_repository),
):
    try:
        workspace = repository.create_workspace_for_user(
            user.user_id,
            email=user.email,
            display_name=request.display_name or user.display_name,
            organization_name=request.organization_name,
            workspace_name=request.workspace_name,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"workspace": workspace}
