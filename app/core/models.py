"""Shared request/response models.
┌────────────────────────────┬────────────────────────────────────────────────────────────────────┐
│ Model                      │ Purpose                                                            │
├────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Citation                   │ Describes retrieved evidence returned with an answer               │
│ RetrievalFilters           │ Limits retrieval to selected documents, types, titles, or metadata │
│ ChatRequest                │ Input to the chat endpoint and support agent                       │
│ ChatResponse               │ Generated answer, citations, evidence status, escalation result    │
│ DocumentRecord             │ Full document ingestion/listing representation                     │
│ DocumentIngestResponse     │ Compact response after upload or URL ingestion                     │
│ UrlIngestRequest           │ URL input payload                                                  │
│ HealthResponse             │ API health/status output                                           │
│ WorkflowRequest            │ Input for support workflow endpoints                               │
│ ConversationSummaryRequest │ Conversation messages supplied for summarization                   │
│ FeedbackRequest            │ User feedback payload                                              │
│ FeedbackResponse           │ Confirmation that feedback was accepted                            │
└────────────────────────────┴────────────────────────────────────────────────────────────────────┘
"""

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
    # Backward-compatible numeric evidence-support heuristic. It is not a
    # calibrated probability that an answer is correct.
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_status: str = "unassessed"
    needs_escalation: bool
    suggested_ticket_reply: str | None = None
    generation_model: str | None = None
    trace_id: str
    conversation_id: str | None = None


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
    startup_error: str | None = None


class WorkflowRequest(BaseModel):
    question: str = Field(min_length=1)


class ConversationSummaryRequest(BaseModel):
    messages: list[str] = Field(min_length=1)


class FeedbackRequest(BaseModel):
    trace_id: str
    rating: int = Field(ge=1, le=5)
    feedback_type: str | None = None
    comment: str | None = None
    corrected_answer: str | None = None


class FeedbackResponse(BaseModel):
    accepted: bool
    trace_id: str
