from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_product_repository, require_admin, _workspace_id
from app.core.persistence import analytics_for

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def analytics(
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    repository=Depends(get_product_repository),
):
    return analytics_for(repository, _workspace_id(x_workspace_id))
