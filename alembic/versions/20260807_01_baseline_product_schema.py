"""Baseline the existing GroundDesk product-interaction schema.

Revision ID: 20260807_01
Revises:
Create Date: 2026-08-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

try:
    from sqlalchemy.dialects import postgresql
except ImportError:  # pragma: no cover - SQLAlchemy always provides this dialect.
    postgresql = None


revision = "20260807_01"
down_revision = None
branch_labels = None
depends_on = None


def _user_id_column(name: str, *, nullable: bool, primary_key: bool = False):
    """Use Supabase Auth foreign keys where its schema is available."""
    if op.get_bind().dialect.name == "postgresql":
        return sa.Column(
            name,
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey(
                "auth.users.id", ondelete="SET NULL" if nullable else "CASCADE"
            ),
            nullable=nullable,
            primary_key=primary_key,
        )
    return sa.Column(
        name,
        sa.Uuid(as_uuid=False),
        nullable=nullable,
        primary_key=primary_key,
    )


def upgrade() -> None:
    timestamp = sa.DateTime(timezone=True)
    now = sa.text("CURRENT_TIMESTAMP")
    citation_json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        _user_id_column("user_id", nullable=True),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
        sa.Column("updated_at", timestamp, nullable=False, server_default=now),
    )
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
    op.create_index(
        "ix_conversations_user_id", "conversations", ["user_id", "updated_at"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(length=64),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        _user_id_column("user_id", nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
        sa.CheckConstraint("role in ('user', 'assistant')", name="ck_messages_role"),
    )
    op.create_index(
        "ix_messages_conversation_id", "messages", ["conversation_id", "created_at"]
    )
    op.create_index(
        "ix_messages_workspace_id", "messages", ["workspace_id", "created_at"]
    )
    op.create_index("ix_messages_trace_id", "messages", ["trace_id"])
    op.create_index("ix_messages_user_id", "messages", ["user_id", "created_at"])

    op.create_table(
        "answer_traces",
        sa.Column("trace_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(length=64),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _user_id_column("user_id", nullable=True),
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "user_message_id",
            sa.String(length=64),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assistant_message_id",
            sa.String(length=64),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "citations", citation_json, nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("suggested_ticket_reply", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "evidence_status",
            sa.String(length=40),
            nullable=False,
            server_default="unassessed",
        ),
        sa.Column("generation_model", sa.String(length=100), nullable=True),
        sa.Column("needs_escalation", sa.Boolean(), nullable=False),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
    )
    op.create_index(
        "ix_answer_traces_workspace_id", "answer_traces", ["workspace_id", "created_at"]
    )
    op.create_index(
        "ix_answer_traces_conversation_id",
        "answer_traces",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_answer_traces_user_id", "answer_traces", ["user_id", "created_at"]
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "trace_id",
            sa.String(length=64),
            sa.ForeignKey("answer_traces.trace_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        _user_id_column("user_id", nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("feedback_type", sa.String(length=64), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("corrected_answer", sa.Text(), nullable=True),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
        sa.CheckConstraint("rating between 1 and 5", name="ck_feedback_rating"),
    )
    op.create_index(
        "ix_feedback_workspace_id", "feedback", ["workspace_id", "created_at"]
    )
    op.create_index("ix_feedback_trace_id", "feedback", ["trace_id"])
    op.create_index("ix_feedback_user_id", "feedback", ["user_id", "created_at"])

    op.create_table(
        "workspace_members",
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        _user_id_column("user_id", nullable=False, primary_key=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
        sa.CheckConstraint(
            "role in ('member', 'knowledge_manager', 'owner')",
            name="ck_workspace_members_role",
        ),
    )
    op.create_index(
        "ix_workspace_members_user_id", "workspace_members", ["user_id", "workspace_id"]
    )

    if op.get_bind().dialect.name == "postgresql":
        _enable_supabase_rls()


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "drop function if exists private.is_grounddesk_workspace_member(varchar)"
        )
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_index("ix_feedback_trace_id", table_name="feedback")
    op.drop_index("ix_feedback_workspace_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_answer_traces_user_id", table_name="answer_traces")
    op.drop_index("ix_answer_traces_conversation_id", table_name="answer_traces")
    op.drop_index("ix_answer_traces_workspace_id", table_name="answer_traces")
    op.drop_table("answer_traces")
    op.drop_index("ix_messages_user_id", table_name="messages")
    op.drop_index("ix_messages_trace_id", table_name="messages")
    op.drop_index("ix_messages_workspace_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_index("ix_conversations_workspace_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("workspaces")


def _enable_supabase_rls() -> None:
    """Apply the existing Supabase defense-in-depth policies to a fresh schema."""
    statements = (
        "alter table workspaces enable row level security",
        "alter table workspace_members enable row level security",
        "alter table conversations enable row level security",
        "alter table messages enable row level security",
        "alter table answer_traces enable row level security",
        "alter table feedback enable row level security",
        "create schema if not exists private",
        """
        create or replace function private.is_grounddesk_workspace_member(target_workspace_id varchar)
        returns boolean language sql security definer set search_path = public stable as $$
          select exists (
            select 1 from public.workspace_members wm
            where wm.workspace_id = target_workspace_id
              and wm.user_id = (select auth.uid())
          );
        $$
        """,
        "revoke all on function private.is_grounddesk_workspace_member(varchar) from public",
        "grant usage on schema private to authenticated",
        "grant execute on function private.is_grounddesk_workspace_member(varchar) to authenticated",
        """
        create policy \"members can view their workspaces\" on workspaces for select to authenticated
        using (private.is_grounddesk_workspace_member(id))
        """,
        """
        create policy \"members can view own membership\" on workspace_members for select to authenticated
        using (user_id = (select auth.uid()))
        """,
        """
        create policy \"members manage own conversations\" on conversations for all to authenticated
        using (user_id = (select auth.uid()) and private.is_grounddesk_workspace_member(workspace_id))
        with check (user_id = (select auth.uid()) and private.is_grounddesk_workspace_member(workspace_id))
        """,
        """
        create policy \"members manage own messages\" on messages for all to authenticated
        using (user_id = (select auth.uid()) and private.is_grounddesk_workspace_member(workspace_id))
        with check (user_id = (select auth.uid()) and private.is_grounddesk_workspace_member(workspace_id))
        """,
        """
        create policy \"members view own traces\" on answer_traces for select to authenticated
        using (user_id = (select auth.uid()) and private.is_grounddesk_workspace_member(workspace_id))
        """,
        """
        create policy \"members manage own feedback\" on feedback for all to authenticated
        using (user_id = (select auth.uid()) and private.is_grounddesk_workspace_member(workspace_id))
        with check (user_id = (select auth.uid()) and private.is_grounddesk_workspace_member(workspace_id))
        """,
    )
    for statement in statements:
        op.execute(sa.text(statement))
