"""FastAPI application for GroundDesk."""

from __future__ import annotations

from pathlib import Path
import tempfile

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
import gradio as gr

from ..generation.agent import SupportAgent
from ..generation.workflows import SupportWorkflowService
from ..core.config import settings
from ..core.persistence import JsonlRepository
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
feedback_repo = JsonlRepository(settings.feedback_path)
chat_history_repo = JsonlRepository(settings.chat_history_path)

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    if not vector_store.has_records():
        ingestion_service.ingest_sample_corpus()


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        app=settings.app_name,
        status="ok",
        documents=len(ingestion_service.list_documents()),
        chunks=vector_store.count_chunks(),
        embedding_model=f"{settings.embedding_model} ({embedding_model.backend})",
    )


@app.get("/api/documents")
def list_documents():
    return ingestion_service.list_documents()


@app.post("/api/documents", response_model=DocumentIngestResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentIngestResponse:
    suffix = Path(file.filename or "document.txt").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        original_filename = file.filename or "document.txt"
        record = ingestion_service.create_uploaded_document(
            tmp_path,
            original_filename=original_filename,
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
async def replace_document(document_id: str, file: UploadFile = File(...)) -> DocumentIngestResponse:
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
def ingest_url(request: UrlIngestRequest) -> DocumentIngestResponse:
    try:
        record = ingestion_service.ingest_url(request.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentIngestResponse(
        document_id=record.document_id,
        status=record.status,
        chunks_indexed=record.chunks_indexed,
        warnings=record.warnings,
    )


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    deleted = vector_store.delete_document(document_id)
    return {"document_id": document_id, "chunks_deleted": deleted}


@app.post("/api/chat")
def chat(request: ChatRequest, x_llm_api_key: str | None = Header(default=None)):
    try:
        response = agent.answer(request, api_key=x_llm_api_key)
        chat_history_repo.append(
            {
                "conversation_id": request.conversation_id,
                "question": request.question,
                "trace_id": response.trace_id,
                "needs_escalation": response.needs_escalation,
                "confidence": response.confidence,
            }
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/evals/run")
def evals():
    return run_evals(agent)


@app.post("/api/evals/retrieval")
def retrieval_evals():
    return run_retrieval_evals(agent.retriever, embedding_model)


@app.post("/api/evals/answers")
def answer_evals():
    return run_answer_quality_evals(agent)


@app.post("/api/evals/synthetic")
def synthetic_evals():
    return generate_synthetic_eval_dataset(vector_store.list_chunks())


@app.post("/api/evals/variants")
def retrieval_variant_evals():
    return compare_retrieval_variants(agent)


@app.post("/api/workflows/escalation-note")
def escalation_note(request: WorkflowRequest):
    return workflows.escalation_note(
        request.question,
        provider=request.provider,
        model=request.model,
    )


@app.post("/api/workflows/conversation-summary")
def conversation_summary(request: ConversationSummaryRequest):
    return workflows.summarize_conversation(request.messages)


@app.post("/api/workflows/knowledge-gap")
def knowledge_gap(request: WorkflowRequest):
    return workflows.knowledge_gap(request.question)


@app.post("/api/workflows/support-article")
def support_article(request: WorkflowRequest):
    return workflows.suggest_support_article(request.question)


@app.get("/api/workflows/documents/{document_id}/summary")
def document_summary(document_id: str):
    document = vector_store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Unknown document_id: {document_id}")
    text = _document_text(document_id)
    return workflows.summarize_document(document.title, text)


@app.get("/api/workflows/documents/{document_id}/faq")
def document_faq(document_id: str):
    document = vector_store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Unknown document_id: {document_id}")
    text = _document_text(document_id)
    return workflows.faq_from_document(document.title, text)


@app.get("/api/workflows/documents/{document_id}/changelog-summary")
def changelog_summary(document_id: str):
    document = vector_store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Unknown document_id: {document_id}")
    text = _document_text(document_id)
    return workflows.summarize_changelog(document.title, text)


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    feedback_repo.append(request.model_dump())
    return FeedbackResponse(accepted=True, trace_id=request.trace_id)


@app.get("/api/history")
def history():
    return chat_history_repo.read_all()


@app.get("/api/analytics")
def analytics():
    history_items = chat_history_repo.read_all()
    feedback_items = feedback_repo.read_all()
    return {
        "messages": len(history_items),
        "feedback_count": len(feedback_items),
        "average_feedback": (
            sum(item["rating"] for item in feedback_items) / len(feedback_items)
            if feedback_items
            else None
        ),
        "unresolved_query_rate": (
            sum(bool(item["needs_escalation"]) for item in history_items) / len(history_items)
            if history_items
            else 0.0
        ),
    }


def _document_text(document_id: str) -> str:
    return "\n\n".join(
        record.text
        for record in vector_store.list_chunks()
        if record.document_id == document_id
    )


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "demo": "/demo",
        "api_docs": "/docs",
        "health": "/api/health",
    }


app = gr.mount_gradio_app(app, build_interface(agent, ingestion_service, vector_store), path="/demo")
