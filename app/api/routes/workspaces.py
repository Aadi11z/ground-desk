from fastapi import APIRouter, Depends

from app.api.dependencies import authenticated_user, get_product_repository
from app.core.auth import AuthenticatedUser

router = APIRouter(tags=["workspaces"])


@router.get("/me/workspaces")
def my_workspaces(
    user: AuthenticatedUser = Depends(authenticated_user),
    repository=Depends(get_product_repository),
):
    return {
        "user_id": user.user_id,
        "email": user.email,
        "workspaces": repository.list_user_workspaces(user.user_id),
    }
