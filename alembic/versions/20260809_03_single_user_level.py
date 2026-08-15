"""Use one workspace user level.

Revision ID: 20260809_03
Revises: 20260808_02
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260809_03"
down_revision = "20260808_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_memberships_workspace_id", table_name="memberships")
    with op.batch_alter_table("memberships") as batch_op:
        batch_op.drop_column("role")
    op.create_index(
        "ix_memberships_workspace_status",
        "memberships",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_memberships_workspace_status", table_name="memberships")
    with op.batch_alter_table("memberships") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=40),
                nullable=False,
                server_default="user",
            )
        )
    op.create_index(
        "ix_memberships_workspace_id",
        "memberships",
        ["workspace_id", "role", "status"],
    )
