"""Shared request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str
    title: str
    chunk_id: str
    snippet: str
    score: float = Field(ge=0.0, le=1.0)
    section_path: list[str] = Field(default_factory=list)
    page_number: int | None = None


class RetrievalFilters(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    draft_ticket_reply: bool = True
    filters: RetrievalFilters | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float = Field(ge=0.0, le=1.0)
    needs_escalation: bool
    suggested_ticket_reply: str | None = None
    trace_id: str


class DocumentRecord(BaseModel):
    document_id: str
    source_id: str
    version_id: str
    content_hash: str
    title: str
    source_type: str
    source: str
    original_filename: str | None = None
    chunks_indexed: int
    ingested_at: str
    status: str
    warnings: list[str] = Field(default_factory=list)
    diagnostics: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentIngestResponse(BaseModel):
    document_id: str
    status: str
    chunks_indexed: int
    warnings: list[str] = Field(default_factory=list)


class UrlIngestRequest(BaseModel):
    url: str = Field(min_length=1)


class HealthResponse(BaseModel):
    app: str
    status: str
    documents: int
    chunks: int
    embedding_model: str


class WorkflowRequest(BaseModel):
    question: str = Field(min_length=1)


class ConversationSummaryRequest(BaseModel):
    messages: list[str] = Field(min_length=1)


class FeedbackRequest(BaseModel):
    trace_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    accepted: bool
    trace_id: str

 
