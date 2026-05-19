"""Gradio UI for SupportIQ."""

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
    embedding_model = EmbeddingModel(settings.embedding_model)
    vector_store = create_vector_store(settings)
    ingestion_service = IngestionService(settings, embedding_model, vector_store)
    from ..generation.agent import SupportAgent

    agent = SupportAgent(settings, embedding_model, vector_store)
    return agent, ingestion_service, vector_store


def ensure_sample_data(ingestion_service: IngestionService, vector_store: VectorStoreBackend) -> str:
    if not vector_store.has_records():
        records = ingestion_service.ingest_sample_corpus()
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


def ask(question: str, provider: str, api_key: str, top_k: int, draft_ticket_reply: bool, agent):
    response = agent.answer(
        ChatRequest(
            question=question,
            provider=provider,
            top_k=int(top_k),
            draft_ticket_reply=draft_ticket_reply,
        ),
        api_key=api_key or None,
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
    with gr.Blocks(title="SupportIQ") as demo:
        gr.Markdown("# SupportIQ\nEvidence-grounded customer support agent with RAG, citations, evals, and deployment-ready APIs.")
        status = gr.Textbox(label="System Status", value=ensure_sample_data(ingestion_service, vector_store), interactive=False)

        with gr.Tab("Chat"):
            with gr.Row():
                question = gr.Textbox(label="Customer Question", lines=4, scale=3)
                with gr.Column(scale=1):
                    provider = gr.Dropdown(["template", "openai", "anthropic", "gemini"], value="template", label="LLM Provider")
                    api_key = gr.Textbox(label="BYO API Key", type="password")
                    top_k = gr.Slider(1, 10, value=5, step=1, label="Retrieved Chunks")
                    draft = gr.Checkbox(label="Draft ticket reply", value=True)
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
                lambda q, p, k, t, d: ask(q, p, k, t, d, agent),
                [question, provider, api_key, top_k, draft],
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
