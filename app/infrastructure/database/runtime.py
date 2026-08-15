"""Lifespan-owned SQLAlchemy engine and request session factory."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import normalize_database_url

if TYPE_CHECKING:
    from collections.abc import Iterator

    from app.infrastructure.config import Settings


@dataclass(frozen=True)
class DatabasePoolConfig:
    size: int
    max_overflow: int
    timeout_seconds: int
    recycle_seconds: int


@dataclass
class DatabaseRuntime:
    """Own the database engine and create bounded request sessions."""

    engine: Engine
    session_factory: sessionmaker[Session]
    pool_config: DatabasePoolConfig

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            if session.in_transaction():
                session.rollback()
            session.close()

    def close(self) -> None:
        self.engine.dispose()


def create_database_runtime(settings: Settings) -> DatabaseRuntime | None:
    if settings.persistence_backend != "database":
        return None
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is required when PERSISTENCE_BACKEND=database."
        )

    pool_config = DatabasePoolConfig(
        size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        timeout_seconds=settings.database_pool_timeout_seconds,
        recycle_seconds=settings.database_pool_recycle_seconds,
    )
    database_url = normalize_database_url(settings.database_url)
    options = _engine_options(settings, database_url, pool_config)
    engine = create_engine(database_url, **options)
    return DatabaseRuntime(
        engine=engine,
        session_factory=sessionmaker(
            bind=engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        ),
        pool_config=pool_config,
    )


def _engine_options(
    settings: Settings,
    database_url: str,
    pool_config: DatabasePoolConfig,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_size": pool_config.size,
        "max_overflow": pool_config.max_overflow,
        "pool_timeout": pool_config.timeout_seconds,
        "pool_recycle": pool_config.recycle_seconds,
    }
    if database_url.startswith("postgresql+psycopg://"):
        options["connect_args"] = {
            "prepare_threshold": (5 if settings.database_prepared_statements else None)
        }
    return options
