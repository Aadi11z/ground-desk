"""Verify an Alembic-managed GroundDesk database and optionally seed demo state."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    if settings.persistence_backend.lower() != "database":
        raise SystemExit(
            "Set PERSISTENCE_BACKEND=database and DATABASE_URL before checking PostgreSQL."
        )
    repository = DatabaseProductRepository(settings.database_url)
    _assert_alembic_at_head(repository)
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
    print(
        json.dumps(
            {
                "database": "ready",
                "auth_mode": settings.auth_mode.lower(),
                "workspace_id": workspace_id,
                "member_seeded": bool(args.member_user_id),
                "membership_role": membership,
                "alembic_revision": _alembic_head(),
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

    now = datetime.now(UTC)
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


def _alembic_head() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(ROOT / "alembic.ini"))
    return ScriptDirectory.from_config(config).get_current_head()


def _assert_alembic_at_head(repository: DatabaseProductRepository) -> None:
    from alembic.runtime.migration import MigrationContext

    expected = _alembic_head()
    with repository.engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    if current != expected:
        raise SystemExit(
            "Database schema revision is unexpected. "
            f"Expected {expected!r}, found {current!r}. Run Alembic upgrade or, "
            "for a reviewed pre-Alembic database, Alembic stamp."
        )


if __name__ == "__main__":
    main()
