"""FastAPI application for GroundDesk."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
import gradio as gr

from ..generation.agent import SupportAgent
from ..generation.workflows import SupportWorkflowService
from ..core.auth import AccessContext, AccessController, AccessError
from ..core.config import settings
from ..core.persistence import analytics_for, create_product_repository
from ..core.workspace import (
    apply_workspace_filter,
    metadata_matches_workspace,
    normalize_workspace_id,
)
from ..retrieval.embeddings import EmbeddingModel
from ..evals.answers import run_answer_quality_evals
from ..evals.golden_set import run_evals
from ..evals.retrieval import run_retrieval_evals
from ..evals.synthetic import generate_synthetic_eval_dataset
from ..evals.variants import compare_retrieval_variants
from ..ingestion.service import IngestionService
from ..core.models import (
    ChatRequest,
    ConversationSummaryRequest,
    DocumentIngestResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    UrlIngestRequest,
    WorkflowRequest,
)
from .ui import build_interface
from .demo_product import demo_product_html
from ..retrieval.factory import create_vector_store


embedding_model = EmbeddingModel(
    settings.embedding_model,
    provider=settings.embedding_provider,
    mrl_dimensions=settings.embedding_dimensions,
)
vector_store = create_vector_store(settings)
ingestion_service = IngestionService(settings, embedding_model, vector_store)
agent = SupportAgent(settings, embedding_model, vector_store)
workflows = SupportWorkflowService(agent)
product_repository = create_product_repository(settings)
access_controller = AccessController(settings, product_repository)

app = FastAPI(title=settings.app_name, version="0.1.0")
startup_error: str | None = None


def _require_admin(
    x_admin_api_key: str | None = Header(default=None, alias="X-Admin-API-Key"),
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=404,
            detail="Management endpoints are disabled until authenticated administration is configured.",
        )
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid admin API key.")


def _workspace_id(value: str | None) -> str:
    try:
        return normalize_workspace_id(value, default=settings.default_workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _normal_access_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> AccessContext:
    try:
        return access_controller.resolve(
            authorization=authorization,
            requested_workspace_id=x_workspace_id,
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _authenticated_access_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> AccessContext:
    try:
        return access_controller.resolve(
            authorization=authorization,
            requested_workspace_id=x_workspace_id,
            require_authenticated=True,
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _ensure_workspace_document(document_id: str, workspace_id: str):
    document = vector_store.get_document(document_id)
    if document is None or not metadata_matches_workspace(
        document.metadata,
        workspace_id,
        default=settings.default_workspace_id,
    ):
        raise HTTPException(
            status_code=404, detail=f"Unknown document_id: {document_id}"
        )
    return document


@app.on_event("startup")
def startup() -> None:
    global startup_error
    try:
        if not vector_store.has_records() or not ingestion_service.list_documents(
            metadata_filter={"workspace_id": settings.default_workspace_id}
        ):
            ingestion_service.ingest_sample_corpus(
                metadata={"workspace_id": settings.default_workspace_id}
            )
        startup_error = None
    except Exception as exc:
        startup_error = str(exc)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    documents = 0
    chunks = 0
    health_error = startup_error
    try:
        vector_store.count_chunks()
        if settings.auth_mode.lower() == "demo":
            demo_documents = ingestion_service.list_documents(
                metadata_filter={"workspace_id": settings.default_workspace_id}
            )
            documents = len(demo_documents)
            chunks = sum(document.chunks_indexed for document in demo_documents)
        product_repository.healthcheck()
        access_controller.healthcheck_configuration()
    except Exception as exc:
        health_error = health_error or str(exc)
    return HealthResponse(
        app=settings.app_name,
        status="degraded" if health_error else "ok",
        documents=documents,
        chunks=chunks,
        embedding_model=f"{settings.embedding_model} ({embedding_model.backend})",
        startup_error=health_error,
    )


@app.get("/api/benchmark/summary")
def benchmark_summary():
    """Return public summaries of reviewed retrieval benchmark artifacts."""
    reports_dir = settings.benchmark_report_path.parent
    report_paths = sorted(reports_dir.glob("*.json")) if reports_dir.exists() else []
    if not report_paths:
        return {"available": False}
    summaries = []
    for path in report_paths:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        summaries.append(
            {
                "created_at": report.get("created_at"),
                "dataset": report.get("dataset", {}),
                "index": report.get("index", {}),
                "runs": [
                    {
                        "strategy": run.get("strategy"),
                        "num_queries": run.get("num_queries"),
                        "metrics": run.get("metrics", {}),
                    }
                    for run in report.get("runs", [])
                ],
            }
        )
    return {"available": bool(summaries), "reports": summaries}


@app.get("/api/documents")
def list_documents(
    context: AccessContext = Depends(_normal_access_context),
):
    return ingestion_service.list_documents(
        metadata_filter={"workspace_id": context.workspace_id}
    )


@app.post("/api/documents", response_model=DocumentIngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> DocumentIngestResponse:
    workspace_id = _workspace_id(x_workspace_id)
    suffix = Path(file.filename or "document.txt").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        original_filename = file.filename or "document.txt"
        record = ingestion_service.create_uploaded_document(
            tmp_path,
            original_filename=original_filename,
            metadata={"workspace_id": workspace_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return DocumentIngestResponse(
        document_id=record.document_id,
        status=record.status,
        chunks_indexed=record.chunks_indexed,
        warnings=record.warnings,
    )


@app.put("/api/documents/{document_id}", response_model=DocumentIngestResponse)
async def replace_document(
    document_id: str,
    file: UploadFile = File(...),
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> DocumentIngestResponse:
    workspace_id = _workspace_id(x_workspace_id)
    _ensure_workspace_document(document_id, workspace_id)
    suffix = Path(file.filename or "document.txt").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        original_filename = file.filename or "document.txt"
        record = ingestion_service.replace_uploaded_document(
            document_id,
            tmp_path,
            original_filename=original_filename,
            metadata={"workspace_id": workspace_id},
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return DocumentIngestResponse(
        document_id=record.document_id,
        status=record.status,
        chunks_indexed=record.chunks_indexed,
        warnings=record.warnings,
    )


@app.post("/api/documents/url", response_model=DocumentIngestResponse)
def ingest_url(
    request: UrlIngestRequest,
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> DocumentIngestResponse:
    workspace_id = _workspace_id(x_workspace_id)
    try:
        record = ingestion_service.ingest_url(
            request.url, metadata={"workspace_id": workspace_id}
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentIngestResponse(
        document_id=record.document_id,
        status=record.status,
        chunks_indexed=record.chunks_indexed,
        warnings=record.warnings,
    )


@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: str,
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    workspace_id = _workspace_id(x_workspace_id)
    _ensure_workspace_document(document_id, workspace_id)
    deleted = vector_store.delete_document(document_id)
    return {"document_id": document_id, "chunks_deleted": deleted}


@app.post("/api/chat")
def chat(
    request: ChatRequest,
    context: AccessContext = Depends(_normal_access_context),
):
    workspace_id = context.workspace_id
    scoped_request = apply_workspace_filter(request, workspace_id)
    try:
        response = agent.answer(scoped_request)
        conversation_id = product_repository.record_answer(
            workspace_id, scoped_request, response, user_id=context.user_id
        )
        return response.model_copy(update={"conversation_id": conversation_id})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/evals/run")
def evals(_: None = Depends(_require_admin)):
    return run_evals(agent)


@app.post("/api/evals/retrieval")
def retrieval_evals(_: None = Depends(_require_admin)):
    return run_retrieval_evals(agent.retriever, embedding_model)


@app.post("/api/evals/answers")
def answer_evals(_: None = Depends(_require_admin)):
    return run_answer_quality_evals(agent)


@app.post("/api/evals/synthetic")
def synthetic_evals(_: None = Depends(_require_admin)):
    return generate_synthetic_eval_dataset(vector_store.list_chunks())


@app.post("/api/evals/variants")
def retrieval_variant_evals(_: None = Depends(_require_admin)):
    return compare_retrieval_variants(agent)


@app.post("/api/workflows/escalation-note")
def escalation_note(request: WorkflowRequest, _: None = Depends(_require_admin)):
    return workflows.escalation_note(request.question)


@app.post("/api/workflows/conversation-summary")
def conversation_summary(
    request: ConversationSummaryRequest, _: None = Depends(_require_admin)
):
    return workflows.summarize_conversation(request.messages)


@app.post("/api/workflows/knowledge-gap")
def knowledge_gap(request: WorkflowRequest, _: None = Depends(_require_admin)):
    return workflows.knowledge_gap(request.question)


@app.post("/api/workflows/support-article")
def support_article(request: WorkflowRequest, _: None = Depends(_require_admin)):
    return workflows.suggest_support_article(request.question)


@app.get("/api/workflows/documents/{document_id}/summary")
def document_summary(
    document_id: str,
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    document = _ensure_workspace_document(document_id, _workspace_id(x_workspace_id))
    text = _document_text(document_id)
    return workflows.summarize_document(document.title, text)


@app.get("/api/workflows/documents/{document_id}/faq")
def document_faq(
    document_id: str,
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    document = _ensure_workspace_document(document_id, _workspace_id(x_workspace_id))
    text = _document_text(document_id)
    return workflows.faq_from_document(document.title, text)


@app.get("/api/workflows/documents/{document_id}/changelog-summary")
def changelog_summary(
    document_id: str,
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    document = _ensure_workspace_document(document_id, _workspace_id(x_workspace_id))
    text = _document_text(document_id)
    return workflows.summarize_changelog(document.title, text)


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback(
    request: FeedbackRequest,
    context: AccessContext = Depends(_normal_access_context),
) -> FeedbackResponse:
    try:
        product_repository.record_feedback(
            context.workspace_id, request, user_id=context.user_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FeedbackResponse(accepted=True, trace_id=request.trace_id)


@app.get("/api/history")
def history(
    context: AccessContext = Depends(_authenticated_access_context),
):
    return product_repository.list_history(context.workspace_id, user_id=context.user_id)


@app.get("/api/me/workspaces")
def my_workspaces(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    try:
        user = access_controller.authenticate(authorization)
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {
        "user_id": user.user_id,
        "email": user.email,
        "workspaces": product_repository.list_user_workspaces(user.user_id),
    }


@app.get("/api/analytics")
def analytics(
    _: None = Depends(_require_admin),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    workspace_id = _workspace_id(x_workspace_id)
    return analytics_for(product_repository, workspace_id)


def _document_text(document_id: str) -> str:
    return "\n\n".join(
        record.text
        for record in vector_store.list_chunks()
        if record.document_id == document_id
    )


@app.get("/")
def product_demo() -> HTMLResponse:
    return HTMLResponse(demo_product_html())


@app.get("/app")
def app_demo() -> HTMLResponse:
    return HTMLResponse(demo_product_html())


if settings.enable_gradio_admin:
    app = gr.mount_gradio_app(
        app, build_interface(agent, ingestion_service, vector_store), path="/demo"
    )
