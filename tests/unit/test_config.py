from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.infrastructure.config import Settings


def test_settings_parse_comma_separated_values_without_dotenv(tmp_path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        embedding_dimensions="384, 768",
        generation_fallback_models="first, second",
    )

    assert settings.embedding_dimensions == (384, 768)
    assert settings.generation_fallback_models == ("first", "second")
    assert settings.documents_dir == tmp_path / "data" / "documents"


def test_production_settings_require_hosted_dependencies():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            _env_file=None,
            app_environment="production",
            database_url="",
            admin_api_key=None,
        )


def test_supabase_settings_require_database_and_disable_runtime_schema_creation():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            _env_file=None,
            app_environment="production",
            persistence_backend="database",
            database_url="",
            supabase_url="http://127.0.0.1:54321",
            supabase_publishable_key="local-key",
            vector_store_backend="qdrant",
            qdrant_url="http://127.0.0.1:6333",
            admin_api_key=None,
        )

    with pytest.raises(ValidationError, match="DATABASE_AUTO_CREATE=false"):
        Settings(
            _env_file=None,
            app_environment="production",
            persistence_backend="database",
            database_url="postgresql+psycopg://grounddesk:password@127.0.0.1:54322/postgres",
            database_auto_create=True,
            supabase_url="http://127.0.0.1:54321",
            supabase_publishable_key="local-key",
            vector_store_backend="qdrant",
            qdrant_url="http://127.0.0.1:6333",
        )


def test_production_settings_accept_explicit_hosted_configuration():
    settings = Settings(
        _env_file=None,
        app_environment="production",
        persistence_backend="database",
        database_url="postgresql+psycopg://grounddesk:password@db.example/grounddesk",
        supabase_url="https://grounddesk.supabase.co",
        supabase_publishable_key="publishable-key",
        vector_store_backend="qdrant",
        qdrant_url="https://qdrant.example",
        admin_api_key=None,
    )

    assert settings.app_environment == "production"
    assert settings.supabase_url_value == "https://grounddesk.supabase.co/"


def test_database_pool_settings_are_bounded():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_pool_size=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_max_overflow=-1)


def test_blank_optional_secrets_do_not_enable_protected_routes():
    settings = Settings(_env_file=None, admin_api_key="", qdrant_api_key="")

    assert settings.admin_api_key_value is None
    assert settings.qdrant_api_key_value is None
