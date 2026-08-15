from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from alembic import command
from app.core.persistence import DatabaseProductRepository

ROOT = Path(__file__).resolve().parents[2]
REVISION = "20260815_04"


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_baseline_upgrades_empty_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'empty.sqlite'}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert {
        "workspaces",
        "profiles",
        "organizations",
        "memberships",
        "conversations",
        "messages",
        "answer_traces",
        "feedback",
    } <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == REVISION
    assert "role" in {
        column["name"] for column in inspect(engine).get_columns("memberships")
    }
    membership_constraints = inspect(engine).get_unique_constraints("memberships")
    assert any(
        constraint["name"] == "uq_memberships_workspace_user"
        and constraint["column_names"] == ["workspace_id", "user_id"]
        for constraint in membership_constraints
    )
    membership_checks = inspect(engine).get_check_constraints("memberships")
    assert any(
        constraint["name"] == "ck_memberships_role"
        and "support_agent" in constraint["sqltext"]
        for constraint in membership_checks
    )

    runtime_database_url = f"sqlite:///{tmp_path / 'runtime.sqlite'}"
    runtime_repository = DatabaseProductRepository(
        runtime_database_url, auto_create=True
    )
    runtime_engine = create_engine(runtime_database_url)
    migrated_columns = {
        table: {column["name"] for column in inspect(engine).get_columns(table)}
        for table in inspect(engine).get_table_names()
        if table != "alembic_version"
    }
    runtime_columns = {
        table: {column["name"] for column in inspect(runtime_engine).get_columns(table)}
        for table in inspect(runtime_engine).get_table_names()
    }

    assert migrated_columns == runtime_columns
    runtime_repository.engine.dispose()
    runtime_engine.dispose()
    engine.dispose()


def test_alembic_stamps_existing_database_without_schema_changes(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'existing.sqlite'}"
    DatabaseProductRepository(database_url, auto_create=True)

    command.stamp(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == REVISION
