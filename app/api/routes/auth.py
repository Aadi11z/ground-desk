"""Authenticated browser identity and organization-provisioning endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    authenticated_user,
    get_product_repository,
)
from app.core.auth import AuthenticatedUser
from app.core.models import WorkspaceOnboardingRequest

router = APIRouter(tags=["authentication"])


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
