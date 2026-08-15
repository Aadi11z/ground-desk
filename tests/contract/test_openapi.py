from __future__ import annotations

import hashlib
import json

from app.infrastructure.config import Settings
from app.main import create_app

OPENAPI_SHA256 = "a6dfe4fdb5aee7f9c9d0482d88ac61804dfd57c19e22092cb7982810c45b646f"


def test_openapi_baseline_is_reviewed():
    settings = Settings(
        _env_file=None,
        app_environment="test",
        data_dir="data",
        sample_dir="sample_corpus",
        embedding_provider="hashing",
        embedding_model="hashing",
        embedding_dimensions=(384,),
        generation_provider="template",
        vector_store_backend="local",
        persistence_backend="jsonl",
        auth_mode="demo",
        admin_api_key="test-admin",
        demo_bootstrap_sample_corpus=False,
    )
    schema = create_app(settings).openapi()
    document = json.dumps(schema, sort_keys=True, separators=(",", ":"))

    assert "/api/benchmark/summary" not in schema["paths"]
    assert hashlib.sha256(document.encode()).hexdigest() == OPENAPI_SHA256
