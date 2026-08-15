# Phase 0 baselines

The deterministic RAG implementation is the reference path. Phase 0 changes
must not alter its retrieval, generation, citation, or escalation behavior.

- Regression baseline before the Phase 0 implementation: **52 tests passed**.
- Current API contract baseline: SHA-256
  `a6dfe4fdb5aee7f9c9d0482d88ac61804dfd57c19e22092cb7982810c45b646f`, enforced
  by `tests/contract/test_openapi.py`.
- Current verified suite: **85 tests passed**.
- Alembic verification is limited to SQLite: upgrading an empty database,
  comparing that schema with the runtime-created schema, and stamping an
  existing runtime schema. It is not evidence of PostgreSQL migration execution
  or Row-Level Security (RLS) behavior.
- Retrieval and answer baseline reports: `benchmarks/reports/nfcorpus_bge.json`,
  `benchmarks/reports/nfcorpus_gemini_slice.json`, and
  `benchmarks/reports/grounddesk_support_gemini_demo_ready.json`.
- Package inventory: the committed root `pyproject.toml` and `uv.lock`.

Run the required baseline checks from the repository root:

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -q
```

Benchmark reports include their own machine-local latency measurements. They
are comparison artifacts, not hosted-service latency claims.
