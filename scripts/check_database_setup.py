"""Verify and optionally provision GroundDesk PostgreSQL/Supabase demo state.

This utility does not run migrations. Apply SQL files first, then use it to
fail fast on missing schema and seed a workspace membership when demonstrating
authenticated mode.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.core.persistence import DatabaseProductRepository  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check GroundDesk database migrations and optionally seed a workspace/member."
    )
    parser.add_argument("--workspace-id", default=None)
    parser.add_argument("--workspace-name", default=None)
    parser.add_argument(
        "--member-user-id",
        default=None,
        help="Existing Supabase Auth user UUID to authorize in the workspace.",
    )
    parser.add_argument(
        "--role",
        choices=("member", "knowledge_manager", "owner"),
        default="member",
    )
    parser.add_argument(
        "--dev-auto-create",
        action="store_true",
        help="Create tables only for a local SQLite smoke test; never use for Supabase.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    if settings.persistence_backend.lower() != "database":
        raise SystemExit(
            "Set PERSISTENCE_BACKEND=database and DATABASE_URL before checking PostgreSQL."
        )
    if args.dev_auto_create and not settings.database_url.startswith("sqlite"):
        raise SystemExit("--dev-auto-create is allowed only with a SQLite DATABASE_URL.")
    repository = DatabaseProductRepository(
        settings.database_url, auto_create=args.dev_auto_create
    )
    repository.healthcheck()
    if settings.auth_mode.lower() == "supabase" or args.member_user_id:
        repository.auth_healthcheck()

    workspace_id = args.workspace_id or settings.default_workspace_id
    if args.workspace_id or args.member_user_id:
        _seed_workspace(
            repository,
            workspace_id=workspace_id,
            workspace_name=args.workspace_name or workspace_id,
            member_user_id=args.member_user_id,
            role=args.role,
        )

    membership = (
        repository.membership_role(args.member_user_id, workspace_id)
        if args.member_user_id
        else None
    )
    migrations = ["0001_product_interactions.sql", "0003_evidence_status.sql"]
    if settings.auth_mode.lower() == "supabase" or args.member_user_id:
        migrations.insert(1, "0002_auth_workspace_membership.sql")
    print(
        json.dumps(
            {
                "database": "ready",
                "auth_mode": settings.auth_mode.lower(),
                "workspace_id": workspace_id,
                "member_seeded": bool(args.member_user_id),
                "membership_role": membership,
                "required_migrations": migrations,
            },
            indent=2,
        )
    )


def _seed_workspace(
    repository: DatabaseProductRepository,
    *,
    workspace_id: str,
    workspace_name: str,
    member_user_id: str | None,
    role: str,
) -> None:
    from sqlalchemy import insert, select, update

    now = datetime.now(timezone.utc)
    with repository.engine.begin() as connection:
        workspace = connection.execute(
            select(repository.workspaces.c.id).where(
                repository.workspaces.c.id == workspace_id
            )
        ).first()
        if workspace is None:
            connection.execute(
                insert(repository.workspaces).values(
                    id=workspace_id, name=workspace_name, created_at=now
                )
            )
        else:
            connection.execute(
                update(repository.workspaces)
                .where(repository.workspaces.c.id == workspace_id)
                .values(name=workspace_name)
            )

        if not member_user_id:
            return
        membership = connection.execute(
            select(repository.workspace_members.c.user_id).where(
                repository.workspace_members.c.workspace_id == workspace_id,
                repository.workspace_members.c.user_id == member_user_id,
            )
        ).first()
        if membership is None:
            connection.execute(
                insert(repository.workspace_members).values(
                    workspace_id=workspace_id,
                    user_id=member_user_id,
                    role=role,
                    created_at=now,
                )
            )
        else:
            connection.execute(
                update(repository.workspace_members)
                .where(
                    repository.workspace_members.c.workspace_id == workspace_id,
                    repository.workspace_members.c.user_id == member_user_id,
                )
                .values(role=role)
            )


if __name__ == "__main__":
    main()
