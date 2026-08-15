"""Add profiles, organizations, and active workspace memberships.

Revision ID: 20260808_02
Revises: 20260807_01
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

try:
    from sqlalchemy.dialects import postgresql
except ImportError:  # pragma: no cover
    postgresql = None


revision = "20260808_02"
down_revision = "20260807_01"
branch_labels = None
depends_on = None


def _user_id_column(name: str, *, nullable: bool, primary_key: bool = False):
    if op.get_bind().dialect.name == "postgresql":
        return sa.Column(
            name,
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
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

    op.create_table(
        "profiles",
        _user_id_column("user_id", nullable=False, primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
        sa.Column("updated_at", timestamp, nullable=False, server_default=now),
    )
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False, unique=True),
        _user_id_column("created_by", nullable=False),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
        sa.Column("updated_at", timestamp, nullable=False, server_default=now),
    )
    op.add_column(
        "workspaces", sa.Column("organization_id", sa.String(length=64), nullable=True)
    )
    op.add_column("workspaces", sa.Column("slug", sa.String(length=200), nullable=True))
    op.add_column(
        "workspaces", sa.Column("status", sa.String(length=32), nullable=True)
    )
    op.add_column("workspaces", _user_id_column("created_by", nullable=True))
    op.add_column(
        "workspaces",
        sa.Column("updated_at", timestamp, nullable=True, server_default=now),
    )
    op.create_index("ix_workspaces_organization_id", "workspaces", ["organization_id"])
    op.create_index(
        "uq_workspaces_organization_slug",
        "workspaces",
        ["organization_id", "slug"],
        unique=True,
    )
    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _user_id_column("user_id", nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="active"
        ),
        sa.Column("created_at", timestamp, nullable=False, server_default=now),
        sa.Column("updated_at", timestamp, nullable=False, server_default=now),
        sa.UniqueConstraint(
            "workspace_id", "user_id", name="uq_memberships_workspace_user"
        ),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id", "status"])
    op.create_index(
        "ix_memberships_workspace_id", "memberships", ["workspace_id", "role", "status"]
    )

    if op.get_bind().dialect.name == "postgresql":
        _enable_identity_rls()


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for statement in (
            'drop policy if exists "members can view own profile" on profiles',
            'drop policy if exists "members can view active memberships" on memberships',
            'drop policy if exists "members can view organizations" on organizations',
        ):
            op.execute(sa.text(statement))
    op.drop_index("ix_memberships_workspace_id", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("uq_workspaces_organization_slug", table_name="workspaces")
    op.drop_index("ix_workspaces_organization_id", table_name="workspaces")
    op.drop_column("workspaces", "updated_at")
    op.drop_column("workspaces", "created_by")
    op.drop_column("workspaces", "status")
    op.drop_column("workspaces", "slug")
    op.drop_column("workspaces", "organization_id")
    op.drop_table("organizations")
    op.drop_table("profiles")


def _enable_identity_rls() -> None:
    statements = (
        "alter table profiles enable row level security",
        "alter table organizations enable row level security",
        "alter table memberships enable row level security",
        """
        create or replace function private.is_grounddesk_workspace_member(target_workspace_id varchar)
        returns boolean language sql security definer set search_path = public stable as $$
          select exists (
            select 1 from public.memberships m
            where m.workspace_id = target_workspace_id
              and m.user_id = (select auth.uid())
              and m.status = 'active'
          ) or exists (
            select 1 from public.workspace_members legacy
            where legacy.workspace_id = target_workspace_id
              and legacy.user_id = (select auth.uid())
          );
        $$
        """,
        """
        create policy "members can view own profile" on profiles for select to authenticated
        using (user_id = (select auth.uid()))
        """,
        """
        create policy "members can view active memberships" on memberships for select to authenticated
        using (user_id = (select auth.uid()))
        """,
        """
        create policy "members can view organizations" on organizations for select to authenticated
        using (exists (
          select 1 from public.workspaces w
          where w.organization_id = organizations.id
            and private.is_grounddesk_workspace_member(w.id)
        ))
        """,
    )
    for statement in statements:
        op.execute(sa.text(statement))
