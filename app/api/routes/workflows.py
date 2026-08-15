from fastapi import APIRouter, Depends

from app.api.dependencies import (
    _document_text,
    _ensure_workspace_document,
    get_vector_store,
    get_workflows,
    normal_access_context,
    require_document_reader,
)
from app.core.auth import AccessContext
from app.core.models import ConversationSummaryRequest, WorkflowRequest

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/escalation-note")
def escalation_note(
    request: WorkflowRequest,
    context: AccessContext = Depends(normal_access_context),
    workflows=Depends(get_workflows),
):
    return workflows.escalation_note(context, request.question)


@router.post("/conversation-summary")
def conversation_summary(
    request: ConversationSummaryRequest,
    _: AccessContext = Depends(normal_access_context),
    workflows=Depends(get_workflows),
):
    return workflows.summarize_conversation(request.messages)


@router.post("/knowledge-gap")
def knowledge_gap(
    request: WorkflowRequest,
    context: AccessContext = Depends(normal_access_context),
    workflows=Depends(get_workflows),
):
    return workflows.knowledge_gap(context, request.question)


@router.post("/support-article")
def support_article(
    request: WorkflowRequest,
    context: AccessContext = Depends(normal_access_context),
    workflows=Depends(get_workflows),
):
    return workflows.suggest_support_article(context, request.question)


def _document_workflow_context(document_id: str, context: AccessContext, store):
    document = _ensure_workspace_document(document_id, context, store=store)
    return document, _document_text(document_id, context, store=store)


@router.get("/documents/{document_id}/summary")
def document_summary(
    document_id: str,
    context: AccessContext = Depends(require_document_reader),
    store=Depends(get_vector_store),
    workflows=Depends(get_workflows),
):
    document, text = _document_workflow_context(document_id, context, store)
    return workflows.summarize_document(document.title, text)


@router.get("/documents/{document_id}/faq")
def document_faq(
    document_id: str,
    context: AccessContext = Depends(require_document_reader),
    store=Depends(get_vector_store),
    workflows=Depends(get_workflows),
):
    document, text = _document_workflow_context(document_id, context, store)
    return workflows.faq_from_document(document.title, text)


@router.get("/documents/{document_id}/changelog-summary")
def changelog_summary(
    document_id: str,
    context: AccessContext = Depends(require_document_reader),
    store=Depends(get_vector_store),
    workflows=Depends(get_workflows),
):
    document, text = _document_workflow_context(document_id, context, store)
    return workflows.summarize_changelog(document.title, text)
