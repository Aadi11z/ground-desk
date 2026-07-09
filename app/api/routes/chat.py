from fastapi import APIRouter, Depends, HTTPException
from app.core.models import ChatRequest
from app.core.auth import AccessContext
from app.api.dependencies import get_agent, normal_access_context, get_product_repository
from app.core.workspace import apply_workspace_filter
from app.core.config import settings

router = APIRouter(tags=["chat"])

@router.post("/chat")
def chat(
    request: ChatRequest,
    context: AccessContext = Depends(normal_access_context),
    agent= Depends(get_agent),
    repository = Depends(get_product_repository)
):
    workspace_id = context.workspace_id
    scoped_request = apply_workspace_filter(request, workspace_id)
    
    try:
        conversation_context = (
            repository.get_conversation_messages(
                workspace_id,
                scoped_request.conversation_id,
                user_id=context.user_id,
                limit=max(1, settings.conversation_context_turns * 2)
            )
            if scoped_request.conversation_id
            else []
        )
        response = agent.answer(
            scoped_request, 
            conversation_context=conversation_context
        )
        conversation_id = repository.record_answer(
            workspace_id,
            scoped_request,
            response,
            user_id=context.user_id
        )
        
        return response.model_copy(update={"conversation_id": conversation_id})

    except ValueError as ex:
        raise HTTPException(status_code=409, detail=str(ex)) from ex
    
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex
    
    