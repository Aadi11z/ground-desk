"""Alembic environment for GroundDesk's application-owned schema."""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The current schema is defined in the reviewed baseline revision. Future ORM
# metadata can be wired here once the repository moves to a session boundary.
target_metadata = None


def database_url() -> str:
    arguments = context.get_x_argument(as_dictionary=True)
    configured_url = config.get_main_option("sqlalchemy.url")
    url = (
        arguments.get("database-url")
        or configured_url
        or os.getenv("DATABASE_MIGRATION_URL")
        or os.getenv("DATABASE_URL")
    )
    if not url:
        raise RuntimeError(
            "DATABASE_MIGRATION_URL or DATABASE_URL is required. "
            "Set one or pass -x database-url=<url>."
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
