from fastapi import APIRouter, Depends
from app.api.dependencies import authenticated_access_context, get_product_repository
from app.core.auth import AccessContext

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def history(
    context: AccessContext = Depends(authenticated_access_context),
    repository=Depends(get_product_repository),
):
    return repository.list_history(context.workspace_id, user_id=context.user_id)
