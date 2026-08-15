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
| Ingestion | Markdown, TXT, PDF text extraction, public HTTP(S) URLs, chunking, quality checks, document/version identity. |
| Retrieval | Local vector store, optional Qdrant adapter, dense retrieval, BM25-style lexical retrieval, hybrid fusion, reranking hooks, context compression. |
| Generation | Gemini provider, deterministic test provider, citations, evidence status, escalation, suggested ticket replies. |
| Persistence | Local SQLite demo state; Alembic revisions define the product schema for profiles, organizations, workspaces, memberships, conversations, messages, traces, and feedback. The verified migration checks are SQLite-only, not PostgreSQL or RLS proof. |
| Access | Login-gated Demo User session locally; Supabase token/membership foundation and transactional workspace onboarding for hosted configuration. |
| Product interface | Dependency-free static HTML/CSS/JavaScript interface at `/` with login, workspace registration, workspace switching, Ask, Documents, and personal History views. |
| API features | Health, client config, documents, chat, feedback, history, analytics, evaluations, workflows, and workspace listing routes. |
| Evaluation | Regression tests, support evaluation set, retrieval evaluation, and benchmark scripts. |
| Local operation | Locked `uv` commands, Python 3.14.6 non-root Docker runtime, Makefile, persisted Demo User/workspace, and runtime document upload. |

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

- The static interface is intentionally small; it is not yet the planned
  separate TypeScript frontend.
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
- The deployment configuration is demo-oriented; Cloud Run and Cloudflare Pages
  are planned, not the current frontend/backend runtime.

## Current Runtime Flow

```text
validated settings
  -> app.main:create_app
  -> lifespan composition root
  -> request dependency providers
  -> existing RAG services in app.rag
  -> local/Qdrant vector storage
  -> JSONL/PostgreSQL interaction persistence
```

The RAG pipeline was moved under `app/rag` without being rewritten.

## Review Order

1. Read this file.
2. Read `app/main.py`, `app/api/router.py`, and `app/api/routes/`.
3. Read `app/api/dependencies.py` and `app/core/auth.py`.
4. Trace `app/rag/ingestion`, `app/rag/retrieval`, and `app/rag/generation`.
5. Run `uv run --locked pytest -q`.
6. Read `docs/PLAN.md` for the next implementation stages.
