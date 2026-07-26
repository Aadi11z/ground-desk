from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.dependencies import get_access_controller, get_product_repository
from app.core.auth import AccessError

router = APIRouter(tags=["workspaces"])


@router.get("/me/workspaces")
def my_workspaces(
    authorization: str | None = Header(default=None, alias="Authorization"),
    access_controller=Depends(get_access_controller),
    repository=Depends(get_product_repository),
):
    try:
        user = access_controller.authenticate(authorization)
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {
        "user_id": user.user_id,
        "email": user.email,
        "workspaces": repository.list_user_workspaces(user.user_id),
    }
