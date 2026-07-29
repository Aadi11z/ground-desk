from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_product_repository, normal_access_context
from app.core.auth import AccessContext
from app.core.models import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
def feedback(
    request: FeedbackRequest,
    context: AccessContext = Depends(normal_access_context),
    repository=Depends(get_product_repository),
) -> FeedbackResponse:
    try:
        repository.record_feedback(
            context.workspace_id, request, user_id=context.user_id
        )
    except KeyError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex

    return FeedbackResponse(accepted=True, trace_id=request.trace_id)
