from fastapi import APIRouter, Depends, Header

from app.api.dependencies import (
    _document_text,
    _ensure_workspace_document,
    _workspace_id,
    get_vector_store,
    get_workflows,
    require_admin,
)
from app.core.models import ConversationSummaryRequest, WorkflowRequest

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/escalation-note")
def escalation_note(
    request: WorkflowRequest,
    _: None = Depends(require_admin),
    workflows=Depends(get_workflows),
):
    return workflows.escalation_note(request.question)


@router.post("/conversation-summary")
def conversation_summary(
    request: ConversationSummaryRequest,
    _: None = Depends(require_admin),
    workflows=Depends(get_workflows),
):
    return workflows.summarize_conversation(request.messages)


@router.post("/knowledge-gap")
def knowledge_gap(
    request: WorkflowRequest,
    _: None = Depends(require_admin),
    workflows=Depends(get_workflows),
):
    return workflows.knowledge_gap(request.question)


@router.post("/support-article")
def support_article(
    request: WorkflowRequest,
    _: None = Depends(require_admin),
    workflows=Depends(get_workflows),
):
    return workflows.suggest_support_article(request.question)


def _document_workflow_context(document_id: str, workspace_id: str, store):
    document = _ensure_workspace_document(document_id, workspace_id, store=store)
    return document, _document_text(document_id, store=store)


@router.get("/documents/{document_id}/summary")
def document_summary(
    document_id: str,
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    store=Depends(get_vector_store),
    workflows=Depends(get_workflows),
):
    document, text = _document_workflow_context(
        document_id, _workspace_id(x_workspace_id), store
    )
    return workflows.summarize_document(document.title, text)


@router.get("/documents/{document_id}/faq")
def document_faq(
    document_id: str,
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    store=Depends(get_vector_store),
    workflows=Depends(get_workflows),
):
    document, text = _document_workflow_context(
        document_id, _workspace_id(x_workspace_id), store
    )
    return workflows.faq_from_document(document.title, text)


@router.get("/documents/{document_id}/changelog-summary")
def changelog_summary(
    document_id: str,
    _: None = Depends(require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    store=Depends(get_vector_store),
    workflows=Depends(get_workflows),
):
    document, text = _document_workflow_context(
        document_id, _workspace_id(x_workspace_id), store
    )
    return workflows.summarize_changelog(document.title, text)
