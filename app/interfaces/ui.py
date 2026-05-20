"""Gradio UI for GroundDesk."""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from ..core.config import settings
from ..retrieval.embeddings import EmbeddingModel
from ..evals.golden_set import run_evals
from ..ingestion.service import IngestionService
from ..core.models import ChatRequest
from ..retrieval.vector_store import VectorStoreBackend
from ..retrieval.factory import create_vector_store

def _services(agent_override=None, ingestion_override=None, store_override=None):
    if agent_override and ingestion_override and store_override:
        return agent_override, ingestion_override, store_override
    embedding_model = EmbeddingModel(
        settings.embedding_model,
        provider=settings.embedding_provider,
        mrl_dimensions=settings.embedding_dimensions,
    )
    vector_store = create_vector_store(settings)
    ingestion_service = IngestionService(settings, embedding_model, vector_store)
    from ..generation.agent import SupportAgent

    agent = SupportAgent(settings, embedding_model, vector_store)
    return agent, ingestion_service, vector_store


def ensure_sample_data(ingestion_service: IngestionService, vector_store: VectorStoreBackend) -> str:
    if not vector_store.has_records():
        records = ingestion_service.ingest_sample_corpus(metadata={"workspace_id": settings.default_workspace_id})
        return f"Loaded {len(records)} sample documents."
    return f"Ready with {len(ingestion_service.list_documents())} documents and {vector_store.count_chunks()} chunks."


def ingest_file(file_obj, ingestion_service: IngestionService) -> str:
    if file_obj is None:
        return "No file selected."
    path = Path(file_obj.name)
    original_filename = path.name
    record = ingestion_service.create_uploaded_document(
        path,
        original_filename=original_filename,
    )
    warning_suffix = f" Warnings: {', '.join(record.warnings)}." if record.warnings else ""
    return f"{record.status}: {record.title}: {record.chunks_indexed} chunks ({record.document_id}).{warning_suffix}"


def ask(question: str, top_k: int, draft_ticket_reply: bool, agent):
    response = agent.answer(
        ChatRequest(
            question=question,
            top_k=int(top_k),
            draft_ticket_reply=draft_ticket_reply,
        )
    )
    citations = "\n\n".join(
        f"[{idx}] {citation.title} / {citation.chunk_id} ({citation.score:.2f})\n{citation.snippet}"
        for idx, citation in enumerate(response.citations, start=1)
    )
    return response.answer, citations, response.suggested_ticket_reply or "", f"{response.confidence:.2f}", str(response.needs_escalation), response.trace_id


def run_eval_ui(agent):
    result = run_evals(agent)
    return result


def build_interface(agent_override=None, ingestion_override=None, store_override=None) -> gr.Blocks:
    agent, ingestion_service, vector_store = _services(agent_override, ingestion_override, store_override)
    with gr.Blocks(title="GroundDesk") as demo:
        gr.Markdown("# GroundDesk\nEvidence-grounded customer support agent with RAG, citations, evals, and deployment-ready APIs.")
        status = gr.Textbox(
            label="System Status",
            value="Admin UI loaded. Use /api/health for current indexing status.",
            interactive=False,
        )

        with gr.Tab("Chat"):
            with gr.Row():
                question = gr.Textbox(label="Customer Question", lines=4, scale=3)
                with gr.Column(scale=1):
                    with gr.Accordion("Advanced retrieval settings", open=False):
                        top_k = gr.Slider(
                            1,
                            10,
                            value=5,
                            step=1,
                            label="Evidence chunks",
                            info="How many retrieved document chunks are passed to Gemini as evidence.",
                        )
                    draft = gr.Checkbox(
                        label="Also draft customer reply",
                        value=True,
                        info="Adds a support-agent style reply that can be pasted into a ticket.",
                    )
                    ask_btn = gr.Button("Answer", variant="primary")
            with gr.Row():
                answer = gr.Textbox(label="Answer", lines=8)
                citations = gr.Textbox(label="Citations", lines=8)
            with gr.Row():
                ticket = gr.Textbox(label="Suggested Ticket Reply", lines=5)
                confidence = gr.Textbox(label="Confidence")
                escalation = gr.Textbox(label="Needs Escalation")
                trace = gr.Textbox(label="Trace ID")
            ask_btn.click(
                lambda q, k, d: ask(q, k, d, agent),
                [question, top_k, draft],
                [answer, citations, ticket, confidence, escalation, trace],
            )

        with gr.Tab("Ingest"):
            upload = gr.File(label="Upload PDF, Markdown, or TXT")
            ingest_btn = gr.Button("Index Document")
            ingest_status = gr.Textbox(label="Ingestion Result")
            ingest_btn.click(lambda file_obj: ingest_file(file_obj, ingestion_service), upload, ingest_status)

        with gr.Tab("Evals"):
            eval_btn = gr.Button("Run Golden Evals")
            eval_output = gr.JSON(label="Eval Results")
            eval_btn.click(lambda: run_eval_ui(agent), None, eval_output)
    return demo


if __name__ == "__main__":
    build_interface().launch(server_name="0.0.0.0", server_port=7860)
