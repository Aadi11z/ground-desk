from __future__ import annotations

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.database.runtime import (
    DatabasePoolConfig,
    DatabaseRuntime,
    _engine_options,
    create_database_runtime,
)


def test_database_runtime_applies_explicit_pool_limits(tmp_path):
    runtime = create_database_runtime(
        Settings(
            _env_file=None,
            persistence_backend="database",
            database_url=f"sqlite:///{tmp_path / 'runtime.db'}",
            database_pool_size=3,
            database_max_overflow=1,
            database_pool_timeout_seconds=7,
            database_pool_recycle_seconds=120,
        )
    )

    assert runtime is not None
    assert runtime.pool_config == DatabasePoolConfig(
        size=3,
        max_overflow=1,
        timeout_seconds=7,
        recycle_seconds=120,
    )
    assert runtime.engine.pool.size() == 3
    runtime.close()


def test_database_runtime_rolls_back_and_closes_failed_request_session():
    class FailedSession:
        rolled_back = False
        closed = False

        def rollback(self):
            self.rolled_back = True

        def in_transaction(self):
            return False

        def close(self):
            self.closed = True

    session = FailedSession()
    runtime = DatabaseRuntime(
        engine=None,
        session_factory=lambda: session,
        pool_config=DatabasePoolConfig(1, 0, 1, 1),
    )

    with pytest.raises(RuntimeError, match="request failed"):
        with runtime.session():
            raise RuntimeError("request failed")

    assert session.rolled_back
    assert session.closed


def test_transaction_pooling_disables_server_prepared_statements():
    settings = Settings(
        _env_file=None,
        database_prepared_statements=False,
    )
    options = _engine_options(
        settings,
        "postgresql+psycopg://grounddesk@example.test/grounddesk",
        DatabasePoolConfig(5, 0, 5, 300),
    )

    assert options["connect_args"] == {"prepare_threshold": None}
