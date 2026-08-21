from __future__ import annotations

import pytest

from app.core.auth import AccessController
from app.core.database import normalize_database_url
from app.infrastructure.config import Settings


@pytest.mark.parametrize(
    ("provided_url", "expected_url"),
    [
        (
            "postgresql://grounddesk:password@localhost/grounddesk",
            "postgresql+psycopg://grounddesk:password@localhost/grounddesk",
        ),
        (
            "postgres://grounddesk:password@localhost/grounddesk",
            "postgresql+psycopg://grounddesk:password@localhost/grounddesk",
        ),
        (
            "postgresql+psycopg2://grounddesk:password@localhost/grounddesk",
            "postgresql+psycopg://grounddesk:password@localhost/grounddesk",
        ),
        (
            "postgresql+psycopg://grounddesk:password@localhost/grounddesk",
            "postgresql+psycopg://grounddesk:password@localhost/grounddesk",
        ),
    ],
)
def test_normalize_database_url_uses_psycopg3(provided_url, expected_url):
    assert normalize_database_url(provided_url) == expected_url


def test_access_controller_rejects_missing_supabase_settings_before_jwks_setup():
    settings = Settings(
        _env_file=None,
        supabase_url=None,
        supabase_publishable_key=None,
    )

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        AccessController(settings, repository=None)
