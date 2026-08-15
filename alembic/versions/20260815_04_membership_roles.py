"""Restore explicit RBAC roles on active memberships.

Revision ID: 20260815_04
Revises: 20260809_03
Create Date: 2026-08-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260815_04"
down_revision = "20260809_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_memberships_workspace_status", table_name="memberships")
    with op.batch_alter_table("memberships") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=40),
                nullable=False,
                # Existing single-level memberships previously managed documents.
                server_default="knowledge_manager",
            )
        )
        batch_op.create_check_constraint(
            "ck_memberships_role",
            "role in ('owner', 'admin', 'knowledge_manager', 'support_agent', 'viewer')",
        )
    op.create_index(
        "ix_memberships_workspace_role_status",
        "memberships",
        ["workspace_id", "role", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_memberships_workspace_role_status", table_name="memberships")
    with op.batch_alter_table("memberships") as batch_op:
        batch_op.drop_constraint("ck_memberships_role", type_="check")
        batch_op.drop_column("role")
    op.create_index(
        "ix_memberships_workspace_status",
        "memberships",
        ["workspace_id", "status"],
    )
