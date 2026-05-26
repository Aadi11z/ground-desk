"""Persistence repositories for product interactions and feedback.

The JSONL implementation remains a zero-setup development fallback.  The
database implementation is the production-shaped path: PostgreSQL owns
conversation, answer-trace, and feedback state while Qdrant continues to own
retrievable vector payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Protocol
import uuid

from .models import ChatRequest, ChatResponse, FeedbackRequest


class ProductRepository(Protocol):
    def healthcheck(self) -> None: ...

    def auth_healthcheck(self) -> None: ...

    def record_answer(
        self,
        workspace_id: str,
        request: ChatRequest,
        response: ChatResponse,
        *,
        user_id: str | None = None,
    ) -> str: ...

    def record_feedback(
        self, workspace_id: str, request: FeedbackRequest, *, user_id: str | None = None
    ) -> None: ...

    def list_history(
        self, workspace_id: str, *, user_id: str | None = None
    ) -> list[dict]: ...

    def list_feedback(self, workspace_id: str) -> list[dict]: ...

    def membership_role(self, user_id: str, workspace_id: str) -> str | None: ...

    def list_user_workspaces(self, user_id: str) -> list[dict]: ...


class JsonlRepository:
    """Append-only local storage retained for development and fallback use."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: dict) -> None:
        enriched = {"created_at": _utcnow_iso(), **payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


class JsonlProductRepository:
    """Local adapter matching the database product repository contract."""

    def __init__(self, feedback_path: Path, chat_history_path: Path):
        self.feedback = JsonlRepository(feedback_path)
        self.history = JsonlRepository(chat_history_path)

    def healthcheck(self) -> None:
        return None

    def auth_healthcheck(self) -> None:
        raise RuntimeError("Authenticated workspaces require database persistence.")

    def record_answer(
        self,
        workspace_id: str,
        request: ChatRequest,
        response: ChatResponse,
        *,
        user_id: str | None = None,
    ) -> str:
        conversation_id = request.conversation_id or _id("conv")
        self.history.append(
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "question": request.question,
                "answer": response.answer,
                "citations": [
                    citation.model_dump() for citation in response.citations
                ],
                "suggested_ticket_reply": response.suggested_ticket_reply,
                "trace_id": response.trace_id,
                "needs_escalation": response.needs_escalation,
                "confidence": response.confidence,
            }
        )
        return conversation_id

    def record_feedback(
        self, workspace_id: str, request: FeedbackRequest, *, user_id: str | None = None
    ) -> None:
        self.feedback.append(
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                **request.model_dump(exclude_none=True),
            }
        )

    def list_history(
        self, workspace_id: str, *, user_id: str | None = None
    ) -> list[dict]:
        return [
            item
            for item in self.history.read_all()
            if item.get("workspace_id") == workspace_id
            and (user_id is None or item.get("user_id") == user_id)
        ]

    def list_feedback(self, workspace_id: str) -> list[dict]:
        return [
            item
            for item in self.feedback.read_all()
            if item.get("workspace_id") == workspace_id
        ]

    def membership_role(self, user_id: str, workspace_id: str) -> str | None:
        return None

    def list_user_workspaces(self, user_id: str) -> list[dict]:
        return []


class DatabaseProductRepository:
    """SQLAlchemy-backed interaction repository compatible with PostgreSQL.

    Run ``migrations/0001_product_interactions.sql`` before enabling this
    backend in a hosted environment. ``auto_create`` is provided only for local
    development and tests.
    """

    def __init__(self, database_url: str, *, auto_create: bool = False):
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is required when PERSISTENCE_BACKEND=database."
            )
        try:
            from sqlalchemy import (
                JSON,
                Boolean,
                Column,
                DateTime,
                Float,
                ForeignKey,
                Integer,
                MetaData,
                String,
                Table,
                Text,
                Uuid,
                create_engine,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Install SQLAlchemy and psycopg to use database persistence."
            ) from exc

        metadata = MetaData()
        self.workspaces = Table(
            "workspaces",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("name", String(200), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        self.conversations = Table(
            "conversations",
            metadata,
            Column("id", String(64), primary_key=True),
            Column(
                "workspace_id",
                String(64),
                ForeignKey("workspaces.id"),
                nullable=False,
                index=True,
            ),
            Column("user_id", Uuid(as_uuid=False), nullable=True, index=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
        )
        self.messages = Table(
            "messages",
            metadata,
            Column("id", String(64), primary_key=True),
            Column(
                "conversation_id",
                String(64),
                ForeignKey("conversations.id"),
                nullable=False,
                index=True,
            ),
            Column(
                "workspace_id",
                String(64),
                ForeignKey("workspaces.id"),
                nullable=False,
                index=True,
            ),
            Column("user_id", Uuid(as_uuid=False), nullable=True, index=True),
            Column("role", String(20), nullable=False),
            Column("content", Text, nullable=False),
            Column("trace_id", String(64), nullable=True, index=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        self.answer_traces = Table(
            "answer_traces",
            metadata,
            Column("trace_id", String(64), primary_key=True),
            Column(
                "conversation_id",
                String(64),
                ForeignKey("conversations.id"),
                nullable=False,
                index=True,
            ),
            Column("user_id", Uuid(as_uuid=False), nullable=True, index=True),
            Column(
                "workspace_id",
                String(64),
                ForeignKey("workspaces.id"),
                nullable=False,
                index=True,
            ),
            Column(
                "user_message_id",
                String(64),
                ForeignKey("messages.id"),
                nullable=False,
            ),
            Column(
                "assistant_message_id",
                String(64),
                ForeignKey("messages.id"),
                nullable=False,
            ),
            Column("question", Text, nullable=False),
            Column("answer", Text, nullable=False),
            Column("citations", JSON, nullable=False),
            Column("suggested_ticket_reply", Text, nullable=True),
            Column("confidence", Float, nullable=False),
            Column("needs_escalation", Boolean, nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        self.feedback = Table(
            "feedback",
            metadata,
            Column("id", String(64), primary_key=True),
            Column(
                "trace_id",
                String(64),
                ForeignKey("answer_traces.trace_id"),
                nullable=False,
                index=True,
            ),
            Column(
                "workspace_id",
                String(64),
                ForeignKey("workspaces.id"),
                nullable=False,
                index=True,
            ),
            Column("user_id", Uuid(as_uuid=False), nullable=True, index=True),
            Column("rating", Integer, nullable=False),
            Column("feedback_type", String(64), nullable=True),
            Column("comment", Text, nullable=True),
            Column("corrected_answer", Text, nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        self.workspace_members = Table(
            "workspace_members",
            metadata,
            Column(
                "workspace_id",
                String(64),
                ForeignKey("workspaces.id"),
                primary_key=True,
            ),
            Column("user_id", Uuid(as_uuid=False), primary_key=True),
            Column("role", String(40), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        self.engine = create_engine(database_url, pool_pre_ping=True)
        if auto_create:
            metadata.create_all(self.engine)

    def healthcheck(self) -> None:
        from sqlalchemy import select

        with self.engine.connect() as connection:
            connection.execute(select(self.workspaces.c.id).limit(1)).first()

    def auth_healthcheck(self) -> None:
        from sqlalchemy import select

        with self.engine.connect() as connection:
            connection.execute(select(self.workspace_members.c.user_id).limit(1)).first()

    def record_answer(
        self,
        workspace_id: str,
        request: ChatRequest,
        response: ChatResponse,
        *,
        user_id: str | None = None,
    ) -> str:
        from sqlalchemy import insert, select, update

        now = _utcnow()
        conversation_id = request.conversation_id or _id("conv")
        user_message_id = _id("msg")
        assistant_message_id = _id("msg")
        citations = [citation.model_dump() for citation in response.citations]

        with self.engine.begin() as connection:
            workspace = connection.execute(
                select(self.workspaces.c.id).where(self.workspaces.c.id == workspace_id)
            ).first()
            if workspace is None:
                connection.execute(
                    insert(self.workspaces).values(
                        id=workspace_id, name=workspace_id, created_at=now
                    )
                )

            conversation = connection.execute(
                select(
                    self.conversations.c.workspace_id, self.conversations.c.user_id
                ).where(
                    self.conversations.c.id == conversation_id
                )
            ).first()
            if conversation is None:
                connection.execute(
                    insert(self.conversations).values(
                        id=conversation_id,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
            elif conversation.workspace_id != workspace_id:
                raise ValueError("Conversation does not belong to this workspace.")
            elif user_id is not None and str(conversation.user_id) != user_id:
                raise ValueError("Conversation does not belong to this user.")
            else:
                connection.execute(
                    update(self.conversations)
                    .where(self.conversations.c.id == conversation_id)
                    .values(updated_at=now)
                )

            connection.execute(
                insert(self.messages),
                [
                    {
                        "id": user_message_id,
                        "conversation_id": conversation_id,
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                        "role": "user",
                        "content": request.question,
                        "trace_id": response.trace_id,
                        "created_at": now,
                    },
                    {
                        "id": assistant_message_id,
                        "conversation_id": conversation_id,
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                        "role": "assistant",
                        "content": response.answer,
                        "trace_id": response.trace_id,
                        "created_at": now,
                    },
                ],
            )
            connection.execute(
                insert(self.answer_traces).values(
                    trace_id=response.trace_id,
                    conversation_id=conversation_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    user_message_id=user_message_id,
                    assistant_message_id=assistant_message_id,
                    question=request.question,
                    answer=response.answer,
                    citations=citations,
                    suggested_ticket_reply=response.suggested_ticket_reply,
                    confidence=response.confidence,
                    needs_escalation=response.needs_escalation,
                    created_at=now,
                )
            )
        return conversation_id

    def record_feedback(
        self, workspace_id: str, request: FeedbackRequest, *, user_id: str | None = None
    ) -> None:
        from sqlalchemy import insert, select

        with self.engine.begin() as connection:
            trace = connection.execute(
                select(self.answer_traces.c.trace_id).where(
                    self.answer_traces.c.trace_id == request.trace_id,
                    self.answer_traces.c.workspace_id == workspace_id,
                    *(
                        [self.answer_traces.c.user_id == user_id]
                        if user_id is not None
                        else []
                    ),
                )
            ).first()
            if trace is None:
                raise KeyError("Unknown trace_id for this workspace.")
            connection.execute(
                insert(self.feedback).values(
                    id=_id("feedback"),
                    trace_id=request.trace_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    rating=request.rating,
                    feedback_type=request.feedback_type,
                    comment=request.comment,
                    corrected_answer=request.corrected_answer,
                    created_at=_utcnow(),
                )
            )

    def list_history(
        self, workspace_id: str, *, user_id: str | None = None
    ) -> list[dict]:
        from sqlalchemy import select

        with self.engine.connect() as connection:
            statement = select(self.answer_traces).where(
                self.answer_traces.c.workspace_id == workspace_id
            )
            if user_id is not None:
                statement = statement.where(self.answer_traces.c.user_id == user_id)
            rows = connection.execute(
                statement
                .order_by(self.answer_traces.c.created_at.desc())
            ).mappings()
            return [_jsonable(dict(row)) for row in rows]

    def list_feedback(self, workspace_id: str) -> list[dict]:
        from sqlalchemy import select

        with self.engine.connect() as connection:
            rows = connection.execute(
                select(self.feedback)
                .where(self.feedback.c.workspace_id == workspace_id)
                .order_by(self.feedback.c.created_at.desc())
            ).mappings()
            return [_jsonable(dict(row)) for row in rows]

    def membership_role(self, user_id: str, workspace_id: str) -> str | None:
        from sqlalchemy import select

        with self.engine.connect() as connection:
            row = connection.execute(
                select(self.workspace_members.c.role).where(
                    self.workspace_members.c.user_id == user_id,
                    self.workspace_members.c.workspace_id == workspace_id,
                )
            ).first()
            return str(row.role) if row else None

    def list_user_workspaces(self, user_id: str) -> list[dict]:
        from sqlalchemy import select

        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    self.workspaces.c.id,
                    self.workspaces.c.name,
                    self.workspace_members.c.role,
                )
                .select_from(
                    self.workspace_members.join(
                        self.workspaces,
                        self.workspace_members.c.workspace_id == self.workspaces.c.id,
                    )
                )
                .where(self.workspace_members.c.user_id == user_id)
                .order_by(self.workspaces.c.name)
            ).mappings()
            return [dict(row) for row in rows]

    def add_workspace_member(
        self, workspace_id: str, user_id: str, *, role: str = "member"
    ) -> None:
        """Test/bootstrap helper; hosted membership management is a later UI feature."""
        from sqlalchemy import insert, select

        now = _utcnow()
        with self.engine.begin() as connection:
            workspace = connection.execute(
                select(self.workspaces.c.id).where(self.workspaces.c.id == workspace_id)
            ).first()
            if workspace is None:
                connection.execute(
                    insert(self.workspaces).values(
                        id=workspace_id, name=workspace_id, created_at=now
                    )
                )
            connection.execute(
                insert(self.workspace_members).values(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role=role,
                    created_at=now,
                )
            )


def create_product_repository(settings) -> ProductRepository:
    if settings.persistence_backend.lower() == "database":
        return DatabaseProductRepository(
            settings.database_url, auto_create=settings.database_auto_create
        )
    return JsonlProductRepository(settings.feedback_path, settings.chat_history_path)


def analytics_for(repository: ProductRepository, workspace_id: str) -> dict:
    history_items = repository.list_history(workspace_id)
    feedback_items = repository.list_feedback(workspace_id)
    return {
        "messages": len(history_items),
        "feedback_count": len(feedback_items),
        "average_feedback": (
            sum(item["rating"] for item in feedback_items) / len(feedback_items)
            if feedback_items
            else None
        ),
        "unresolved_query_rate": (
            sum(bool(item["needs_escalation"]) for item in history_items)
            / len(history_items)
            if history_items
            else 0.0
        ),
    }


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _jsonable(payload: dict) -> dict:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in payload.items()
    }
