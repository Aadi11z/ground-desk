"""Persistence repositories for product interactions and feedback.

The JSONL implementation remains a zero-setup development fallback.  The
database implementation is the production-shaped path: PostgreSQL owns
conversation, answer-trace, and feedback state while Qdrant continues to own
retrievable vector payloads.
"""

from __future__ import annotations

import json
import re
import uuid
from contextlib import contextmanager
from copy import copy
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.domain.permissions import WorkspaceRole
from app.domain.tenancy import ActiveMembership

from .database import normalize_database_url
from .models import ChatRequest, ChatResponse, FeedbackRequest


class ProductRepository(Protocol):
    def bind_session(self, session) -> ProductRepository: ...

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

    def get_conversation_messages(
        self,
        workspace_id: str,
        conversation_id: str,
        *,
        user_id: str | None = None,
        limit: int = 8,
    ) -> list[dict]: ...

    def list_feedback(self, workspace_id: str) -> list[dict]: ...

    def has_workspace_membership(self, user_id: str, workspace_id: str) -> bool: ...

    def get_active_membership(
        self, user_id: str, workspace_id: str
    ) -> ActiveMembership | None: ...

    def list_user_workspaces(self, user_id: str) -> list[dict]: ...

    def get_profile(self, user_id: str) -> dict | None: ...

    def create_workspace_for_user(
        self,
        user_id: str,
        *,
        email: str | None,
        display_name: str | None,
        organization_name: str,
        workspace_name: str,
    ) -> dict: ...

    def ensure_demo_identity(
        self, *, user_id: str, email: str, display_name: str, workspace_id: str
    ) -> None: ...


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

    def bind_session(self, session) -> JsonlProductRepository:
        return self

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
                "citations": [citation.model_dump() for citation in response.citations],
                "suggested_ticket_reply": response.suggested_ticket_reply,
                "trace_id": response.trace_id,
                "needs_escalation": response.needs_escalation,
                "confidence": response.confidence,
                "evidence_status": response.evidence_status,
                "generation_model": response.generation_model,
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

    def get_conversation_messages(
        self,
        workspace_id: str,
        conversation_id: str,
        *,
        user_id: str | None = None,
        limit: int = 8,
    ) -> list[dict]:
        history = [
            item
            for item in self.list_history(workspace_id, user_id=user_id)
            if item.get("conversation_id") == conversation_id
        ]
        if not history:
            raise ValueError("Conversation is not available in this workspace.")
        messages: list[dict] = []
        for item in history:
            messages.extend(
                [
                    {"role": "user", "content": item.get("question", "")},
                    {"role": "assistant", "content": item.get("answer", "")},
                ]
            )
        return messages[-max(1, limit) :]

    def list_feedback(self, workspace_id: str) -> list[dict]:
        return [
            item
            for item in self.feedback.read_all()
            if item.get("workspace_id") == workspace_id
        ]

    def has_workspace_membership(self, user_id: str, workspace_id: str) -> bool:
        return False

    def get_active_membership(
        self, user_id: str, workspace_id: str
    ) -> ActiveMembership | None:
        return None

    def list_user_workspaces(self, user_id: str) -> list[dict]:
        return []

    def get_profile(self, user_id: str) -> dict | None:
        return None

    def create_workspace_for_user(
        self,
        user_id: str,
        *,
        email: str | None,
        display_name: str | None,
        organization_name: str,
        workspace_name: str,
    ) -> dict:
        raise RuntimeError("Workspace registration requires database persistence.")

    def ensure_demo_identity(
        self, *, user_id: str, email: str, display_name: str, workspace_id: str
    ) -> None:
        return None


class DatabaseProductRepository:
    """SQLAlchemy-backed interaction repository compatible with PostgreSQL.

    Run the reviewed Alembic migration history before enabling this backend in
    a hosted environment. ``auto_create`` is retained only for isolated tests;
    production settings reject it.
    """

    def __init__(
        self,
        database_url: str,
        *,
        auto_create: bool = False,
        engine=None,
    ):
        if engine is None and not database_url:
            raise RuntimeError(
                "DATABASE_URL is required when PERSISTENCE_BACKEND=database."
            )
        database_url = normalize_database_url(database_url)
        try:
            from sqlalchemy import (
                JSON,
                Boolean,
                CheckConstraint,
                Column,
                DateTime,
                Float,
                ForeignKey,
                Integer,
                MetaData,
                String,
                Table,
                Text,
                UniqueConstraint,
                Uuid,
                create_engine,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Install SQLAlchemy and psycopg to use database persistence."
            ) from exc

        metadata = MetaData()
        self.profiles = Table(
            "profiles",
            metadata,
            Column("user_id", Uuid(as_uuid=False), primary_key=True),
            Column("email", String(320), nullable=True),
            Column("display_name", String(120), nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
        )
        self.organizations = Table(
            "organizations",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("name", String(200), nullable=False),
            Column("slug", String(200), nullable=False, unique=True),
            Column("created_by", Uuid(as_uuid=False), nullable=False, index=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
        )
        self.workspaces = Table(
            "workspaces",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("name", String(200), nullable=False),
            Column("organization_id", String(64), nullable=True, index=True),
            Column("slug", String(200), nullable=True),
            Column("status", String(32), nullable=True),
            Column("created_by", Uuid(as_uuid=False), nullable=True, index=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=True),
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
            Column("evidence_status", String(40), nullable=False),
            Column("generation_model", String(100), nullable=True),
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
        self.memberships = Table(
            "memberships",
            metadata,
            Column("id", String(64), primary_key=True),
            Column(
                "workspace_id",
                String(64),
                ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            Column("user_id", Uuid(as_uuid=False), nullable=False, index=True),
            Column("role", String(40), nullable=False),
            Column("status", String(32), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
            UniqueConstraint(
                "workspace_id", "user_id", name="uq_memberships_workspace_user"
            ),
            CheckConstraint(
                "role in ('owner', 'admin', 'knowledge_manager', "
                "'support_agent', 'viewer')",
                name="ck_memberships_role",
            ),
        )
        self.engine = engine or create_engine(
            database_url,
            pool_pre_ping=True,
            max_overflow=0,
        )
        self._owns_engine = engine is None
        self._session = None
        if auto_create:
            metadata.create_all(self.engine)

    def bind_session(self, session) -> DatabaseProductRepository:
        repository = copy(self)
        repository._session = session
        repository._owns_engine = False
        return repository

    @contextmanager
    def _operation(self):
        if self._session is None:
            with self.engine.begin() as connection:
                yield connection
            return
        with self._session.begin():
            yield self._session

    def close(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    def healthcheck(self) -> None:
        from sqlalchemy import select

        with self._operation() as connection:
            connection.execute(select(self.workspaces.c.id).limit(1)).first()
            connection.execute(select(self.conversations.c.user_id).limit(1)).first()
            connection.execute(select(self.messages.c.user_id).limit(1)).first()
            connection.execute(select(self.answer_traces.c.user_id).limit(1)).first()
            connection.execute(
                select(self.answer_traces.c.evidence_status).limit(1)
            ).first()
            connection.execute(
                select(self.answer_traces.c.generation_model).limit(1)
            ).first()
            connection.execute(select(self.feedback.c.user_id).limit(1)).first()

    def auth_healthcheck(self) -> None:
        from sqlalchemy import select

        with self._operation() as connection:
            connection.execute(select(self.memberships.c.user_id).limit(1)).first()

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

        with self._operation() as connection:
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
                ).where(self.conversations.c.id == conversation_id)
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
                    evidence_status=response.evidence_status,
                    generation_model=response.generation_model,
                    needs_escalation=response.needs_escalation,
                    created_at=now,
                )
            )
        return conversation_id

    def record_feedback(
        self, workspace_id: str, request: FeedbackRequest, *, user_id: str | None = None
    ) -> None:
        from sqlalchemy import insert, select

        with self._operation() as connection:
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

        with self._operation() as connection:
            statement = select(self.answer_traces).where(
                self.answer_traces.c.workspace_id == workspace_id
            )
            if user_id is not None:
                statement = statement.where(self.answer_traces.c.user_id == user_id)
            rows = connection.execute(
                statement.order_by(self.answer_traces.c.created_at.desc())
            ).mappings()
            return [_jsonable(dict(row)) for row in rows]

    def get_conversation_messages(
        self,
        workspace_id: str,
        conversation_id: str,
        *,
        user_id: str | None = None,
        limit: int = 8,
    ) -> list[dict]:
        from sqlalchemy import select

        with self._operation() as connection:
            conversation_statement = select(self.conversations.c.id).where(
                self.conversations.c.id == conversation_id,
                self.conversations.c.workspace_id == workspace_id,
            )
            if user_id is not None:
                conversation_statement = conversation_statement.where(
                    self.conversations.c.user_id == user_id
                )
            if connection.execute(conversation_statement).first() is None:
                raise ValueError("Conversation is not available in this workspace.")

            statement = select(
                self.messages.c.role,
                self.messages.c.content,
                self.messages.c.created_at,
            ).where(
                self.messages.c.conversation_id == conversation_id,
                self.messages.c.workspace_id == workspace_id,
            )
            if user_id is not None:
                statement = statement.where(self.messages.c.user_id == user_id)
            rows = list(
                connection.execute(
                    statement.order_by(
                        self.messages.c.created_at.desc(),
                        self.messages.c.role.asc(),
                    ).limit(max(1, limit))
                ).mappings()
            )
            rows.reverse()
            return [
                {"role": str(row["role"]), "content": str(row["content"])}
                for row in rows
            ]

    def list_feedback(self, workspace_id: str) -> list[dict]:
        from sqlalchemy import select

        with self._operation() as connection:
            rows = connection.execute(
                select(self.feedback)
                .where(self.feedback.c.workspace_id == workspace_id)
                .order_by(self.feedback.c.created_at.desc())
            ).mappings()
            return [_jsonable(dict(row)) for row in rows]

    def has_workspace_membership(self, user_id: str, workspace_id: str) -> bool:
        return self.get_active_membership(user_id, workspace_id) is not None

    def get_active_membership(
        self, user_id: str, workspace_id: str
    ) -> ActiveMembership | None:
        from sqlalchemy import select

        with self._operation() as connection:
            row = connection.execute(
                select(self.memberships.c.role, self.memberships.c.status).where(
                    self.memberships.c.user_id == user_id,
                    self.memberships.c.workspace_id == workspace_id,
                )
            ).first()
            if row is not None:
                # Canonical membership status takes precedence over legacy rows.
                if row.status != "active":
                    return None
                try:
                    role = WorkspaceRole(row.role)
                except ValueError:
                    return None
                return ActiveMembership(
                    workspace_id=workspace_id, user_id=user_id, role=role
                )
            legacy = connection.execute(
                select(self.workspace_members.c.role).where(
                    self.workspace_members.c.user_id == user_id,
                    self.workspace_members.c.workspace_id == workspace_id,
                )
            ).first()
            if legacy is None:
                return None
            try:
                role = WorkspaceRole(legacy.role)
            except ValueError:
                return None
            return ActiveMembership(
                workspace_id=workspace_id, user_id=user_id, role=role
            )

    def list_user_workspaces(self, user_id: str) -> list[dict]:
        from sqlalchemy import select

        with self._operation() as connection:
            rows = connection.execute(
                select(
                    self.workspaces.c.id,
                    self.workspaces.c.name,
                )
                .select_from(
                    self.memberships.join(
                        self.workspaces,
                        self.memberships.c.workspace_id == self.workspaces.c.id,
                    )
                )
                .where(
                    self.memberships.c.user_id == user_id,
                    self.memberships.c.status == "active",
                )
                .order_by(self.workspaces.c.name)
            ).mappings()
            result = {str(row["id"]): dict(row) for row in rows}
            legacy_rows = connection.execute(
                select(
                    self.workspaces.c.id,
                    self.workspaces.c.name,
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
            for row in legacy_rows:
                result.setdefault(str(row["id"]), dict(row))
            return sorted(result.values(), key=lambda workspace: workspace["name"])

    def add_workspace_member(
        self,
        workspace_id: str,
        user_id: str,
        *,
        role: WorkspaceRole = WorkspaceRole.KNOWLEDGE_MANAGER,
    ) -> None:
        """Test/bootstrap helper; hosted membership management is a later UI feature."""
        from sqlalchemy import insert, select

        now = _utcnow()
        with self._operation() as connection:
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
                    role=role.value,
                    created_at=now,
                )
            )
            connection.execute(
                insert(self.memberships).values(
                    id=_id("membership"),
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role=role.value,
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_profile(self, user_id: str) -> dict | None:
        from sqlalchemy import select

        with self._operation() as connection:
            row = (
                connection.execute(
                    select(self.profiles).where(self.profiles.c.user_id == user_id)
                )
                .mappings()
                .first()
            )
            return _jsonable(dict(row)) if row else None

    def create_workspace_for_user(
        self,
        user_id: str,
        *,
        email: str | None,
        display_name: str | None,
        organization_name: str,
        workspace_name: str,
    ) -> dict:
        from sqlalchemy import insert, select

        now = _utcnow()
        organization_name = organization_name.strip()
        workspace_name = workspace_name.strip()
        if not organization_name or not workspace_name:
            raise ValueError("Organization and workspace names are required.")
        organization_id = _id("org")
        workspace_id = _id("workspace")
        organization_slug = _slug(organization_name)
        workspace_slug = _slug(workspace_name)

        with self._operation() as connection:
            if connection.execute(
                select(self.organizations.c.id).where(
                    self.organizations.c.slug == organization_slug
                )
            ).first():
                raise ValueError("An organization with that name already exists.")
            profile = connection.execute(
                select(self.profiles.c.user_id).where(
                    self.profiles.c.user_id == user_id
                )
            ).first()
            if profile is None:
                connection.execute(
                    insert(self.profiles).values(
                        user_id=user_id,
                        email=email,
                        display_name=display_name,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                connection.execute(
                    self.profiles.update()
                    .where(self.profiles.c.user_id == user_id)
                    .values(
                        email=email,
                        display_name=display_name,
                        updated_at=now,
                    )
                )
            connection.execute(
                insert(self.organizations).values(
                    id=organization_id,
                    name=organization_name,
                    slug=organization_slug,
                    created_by=user_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            connection.execute(
                insert(self.workspaces).values(
                    id=workspace_id,
                    name=workspace_name,
                    organization_id=organization_id,
                    slug=workspace_slug,
                    status="active",
                    created_by=user_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            connection.execute(
                insert(self.memberships).values(
                    id=_id("membership"),
                    workspace_id=workspace_id,
                    user_id=user_id,
                    role=WorkspaceRole.OWNER.value,
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
        return {"id": workspace_id, "name": workspace_name}

    def ensure_demo_identity(
        self, *, user_id: str, email: str, display_name: str, workspace_id: str
    ) -> None:
        from sqlalchemy import insert, select

        now = _utcnow()
        organization_id = "grounddesk-demo"
        with self._operation() as connection:
            if (
                connection.execute(
                    select(self.profiles.c.user_id).where(
                        self.profiles.c.user_id == user_id
                    )
                ).first()
                is None
            ):
                connection.execute(
                    insert(self.profiles).values(
                        user_id=user_id,
                        email=email,
                        display_name=display_name,
                        created_at=now,
                        updated_at=now,
                    )
                )
            if (
                connection.execute(
                    select(self.organizations.c.id).where(
                        self.organizations.c.id == organization_id
                    )
                ).first()
                is None
            ):
                connection.execute(
                    insert(self.organizations).values(
                        id=organization_id,
                        name="GroundDesk Demo",
                        slug="grounddesk-demo",
                        created_by=user_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
            if (
                connection.execute(
                    select(self.workspaces.c.id).where(
                        self.workspaces.c.id == workspace_id
                    )
                ).first()
                is None
            ):
                connection.execute(
                    insert(self.workspaces).values(
                        id=workspace_id,
                        name="Demo Workspace",
                        organization_id=organization_id,
                        slug="demo",
                        status="active",
                        created_by=user_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
            if (
                connection.execute(
                    select(self.memberships.c.id).where(
                        self.memberships.c.workspace_id == workspace_id,
                        self.memberships.c.user_id == user_id,
                    )
                ).first()
                is None
            ):
                connection.execute(
                    insert(self.memberships).values(
                        id="membership_grounddesk_demo",
                        workspace_id=workspace_id,
                        user_id=user_id,
                        role=WorkspaceRole.OWNER.value,
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )


def create_product_repository(settings, *, database_runtime=None) -> ProductRepository:
    if settings.persistence_backend.lower() == "database":
        return DatabaseProductRepository(
            settings.database_url,
            auto_create=settings.database_auto_create,
            engine=database_runtime.engine if database_runtime is not None else None,
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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("Names must contain at least one letter or number.")
    return slug[:180]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _jsonable(payload: dict) -> dict:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in payload.items()
    }
