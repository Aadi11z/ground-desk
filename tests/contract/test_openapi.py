from __future__ import annotations

import hashlib
import json

from app.infrastructure.config import Settings
from app.main import create_app

OPENAPI_SHA256 = "0d6eadbf3b1221c1a13effe00440ff1e5a1e355651f7bb975cdc097814b49734"


def test_openapi_baseline_is_reviewed():
    settings = Settings(
        _env_file=None,
        app_environment="test",
        data_dir="data",
        corpus_dir="corpus",
        embedding_provider="hashing",
        embedding_model="hashing",
        embedding_dimensions=(384,),
        generation_provider="template",
        vector_store_backend="local",
        persistence_backend="database",
        database_url="sqlite://",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="publishable-key",
        admin_api_key="test-admin",
    )
    schema = create_app(settings).openapi()
    document = json.dumps(schema, sort_keys=True, separators=(",", ":"))

    assert "/api/benchmark/summary" not in schema["paths"]
    assert hashlib.sha256(document.encode()).hexdigest() == OPENAPI_SHA256
