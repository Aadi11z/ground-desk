# Current State

This is the short source of truth for the repository as it exists now.

## Product

GroundDesk is a support-agent RAG foundation. A user asks a question, the
backend retrieves workspace-scoped evidence, generates an answer, returns
citations, and escalates when the evidence is weak or missing.

## Implemented

| Area | State |
| --- | --- |
| API structure | FastAPI factory in `app/main.py`; lifespan-owned services from `app/bootstrap.py`; modular routers in `app/api`. |
| Ingestion | Markdown, TXT, and PDF text extraction, chunking, quality checks, and document/version identity. |
| Retrieval | Local vector store, optional Qdrant adapter, dense retrieval, BM25-style lexical retrieval, hybrid fusion, and context compression. |
| Generation | Gemini provider, deterministic test provider, citations, evidence status, escalation, suggested ticket replies. |
| Persistence | Supabase/PostgreSQL-shaped persistence; Alembic revisions define the product schema for profiles, organizations, workspaces, memberships, conversations, messages, traces, and feedback. The verified migration checks are SQLite-only, not PostgreSQL or RLS proof. |
| Access | Supabase token verification, membership enforcement, and transactional workspace onboarding. |
| Product interface | Separate React/TypeScript/Vite interface in `frontend/`; FastAPI exposes API and health routes only. The local Vite server proxies API requests during development. |
| API features | Health, client config, authenticated identity/workspace listing, document upload/lifecycle, and chat. |
| Evaluation | Regression tests, support evaluation set, retrieval evaluation, and benchmark scripts. |
| Local operation | Locked `uv` commands, Python 3.14.6 non-root Docker runtime, Supabase-backed configuration, and runtime document upload. |

## Active MVP Boundary

The current product surface is intentionally limited to organization sign-in,
authorized workspace selection, document upload and lifecycle, hybrid retrieval,
and cited chat with safe escalation. Evaluation tooling remains internal; URL
ingestion, trial-corpus loading, feedback/history/analytics APIs, support
workflows, and experimental graph retrieval are deferred.

## Verified

The current refactor has been verified with:

```text
85 tests passed
app.main:app imports successfully
On SQLite, Alembic upgrades an empty database, matches the runtime-created schema, and stamps an existing runtime schema
```

The Alembic checks above do not verify PostgreSQL migration execution or
Row-Level Security (RLS) policies.

## Not Production-Ready

- The React interface is local-development ready; Cloudflare Pages deployment,
  production CORS configuration, and browser end-to-end coverage remain work
  to complete before calling it a hosted frontend.
- Document uploads run synchronously and use local temporary files.
- Document metadata and chunks are not yet managed through a complete
  tenant-safe SQLAlchemy production model.
- There is no Redis queue or background ingestion worker.
- The current management boundary still includes a temporary local admin API key.
- Tenant isolation has unit-level foundations but needs API/integration tests.
- PostgreSQL migration execution and RLS policy behavior have not yet been
  verified by integration tests.
- Document preview shows extracted text only; it is not yet a full source
  viewer with exact document/page highlighting.
- Rate limiting, audit logging, and complete monitoring are still pending.
- Cloud Run and Cloudflare Pages deployment configuration remains planned rather
  than the current frontend/backend runtime.

## Current Runtime Flow

```text
validated settings
  -> app.main:create_app
  -> lifespan composition root
  -> request dependency providers
  -> existing RAG services in app.rag
  -> local/Qdrant vector storage
  -> PostgreSQL interaction persistence
```

The RAG pipeline was moved under `app/rag` without being rewritten.

## Review Order

1. Read this file.
2. Read `app/main.py`, `app/api/router.py`, and `app/api/routes/`.
3. Read `app/api/dependencies.py` and `app/core/auth.py`.
4. Trace `app/rag/ingestion`, `app/rag/retrieval`, and `app/rag/generation`.
5. Run `uv run --locked pytest -q`.
6. Read `docs/PLAN.md` for the next implementation stages.
