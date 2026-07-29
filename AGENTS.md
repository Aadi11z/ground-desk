# GroundDesk Agent Guide

`docs/PLAN.md` is the architecture and implementation source of truth. Execute
only the assigned phase/task; do not treat proposed technology as implemented.

## Product Contract

GroundDesk is a multi-tenant B2B support RAG product. It ingests company
documents, retrieves workspace-authorized evidence, returns cited answers, and
escalates when evidence is insufficient.

Preserve these behaviors:

- deterministic dense + lexical + RRF retrieval is the default;
- citations come only from retrieved evidence;
- weak/conflicting evidence fails closed to clarification or escalation;
- local hashing embeddings and template generation remain usable for tests;
- advanced, multimodal, and agentic paths stay feature-flagged until evaluated.

## Current And Target Stack

| Area | Direction |
| --- | --- |
| Runtime/tooling | Current Python 3.14, root `uv` project/lock, Ruff, pytest; the plan's Python 3.13 target needs a separate compatibility decision. |
| API/config | FastAPI, Uvicorn, Pydantic v2, `pydantic-settings` |
| Data | SQLAlchemy 2, Alembic, psycopg 3, Supabase Postgres |
| Identity/assets | Supabase Auth and private Supabase Storage |
| Retrieval | Existing hybrid RAG; Qdrant with mandatory workspace filters |
| AI | Gemini behind embedding/generation interfaces; deterministic local adapters |
| Jobs | Durable Postgres jobs; inline locally, Cloud Tasks to Cloud Run worker when implemented |
| Deployment | Cloud Run API/worker, Cloudflare Pages frontend, GitHub Actions |
| Operations | Structured redacted logs, Sentry, explicit latency/cost/security metrics |

Today, local files, synchronous ingestion, and some demo/admin-key behavior
still exist. Migrate them only in the order defined by the plan.

## Dependency Direction

```text
API -> application use cases -> domain
                         \-> declared ports <- infrastructure adapters
application -> RAG facade -> existing RAG subsystem
bootstrap/lifespan -> concrete adapters
```

- `api`: HTTP only; no direct SQL, Qdrant, storage, or Gemini calls.
- `application`: use-case orchestration and transaction boundaries.
- `domain`: tenancy, permissions, documents, jobs, evidence, and citation rules;
  no FastAPI or vendor imports.
- `infrastructure`: Postgres, Supabase, Qdrant, Gemini, jobs, security, telemetry.
- `rag`: parsing, indexing, retrieval, routing, context, generation,
  verification, citations, and evaluation; no HTTP authorization.
- `agents`: create only for an approved Phase 6 bounded workflow.
- `workers`: invoke application use cases; do not duplicate ingestion logic.

Do not create empty layers in advance. Move one tested vertical capability at a
time and keep compatibility imports temporary and tracked for removal.

## Non-Negotiable Rules

### Tenancy And Authorization

- Treat `workspace_id` as a security boundary.
- Derive a typed tenant scope after JWT and membership checks; never trust a
  header/path ID alone.
- Require scope in every Postgres, Qdrant, storage, cache, retrieval, analytics,
  update, count, and delete operation.
- Return `404` for inaccessible tenant resources.
- Supabase proves identity; backend permissions authorize actions; RLS is
  defense in depth.
- Replace admin API-key behavior with named RBAC permissions.
- Add a negative cross-workspace test for every new data path.

### RAG, Models, And Tools

- Do not rewrite or replace the hybrid retriever without baseline evidence and
  explicit approval.
- Treat prompts, documents, OCR, retrieved content, and model output as
  untrusted.
- Never put authorization or sensitive-action decisions in prompts.
- Models may use only typed, allowlisted tools with backend-injected scope,
  permission checks, hard budgets, and audit records.
- No unrestricted web retrieval, general agent loop, or multi-agent system.
- Never report generated confidence as calibrated accuracy.

### Data And Ingestion

- Postgres owns metadata/jobs/citations; private object storage owns bytes;
  Qdrant contains rebuildable vectors.
- Do not use Cloud Run local files or Redis as production source of truth.
- Keep document versions immutable and ingestion idempotent by workspace,
  version, and pipeline version.
- Never edit an applied migration; add a reviewed Alembic revision.
- Use expand/contract migrations and preserve rollback compatibility.
- Uploaded files and URLs require allowlists, byte/resource limits, private
  storage, SSRF controls, isolated parsing, and safe deletion.

### Citations And Privacy

- Persist citations against the exact answer, document version, evidence item,
  page/span, and geometry.
- Resolve source assets through authorized opaque citation IDs and short-lived
  signed URLs; never accept arbitrary storage keys.
- Do not log JWTs, secrets, signed URLs, prompts, or full document text.
- Do not send confidential customer data through provider free tiers whose
  terms allow data use or lack required guarantees.

## Change Process

1. Read the relevant `docs/PLAN.md` phase, current implementation, and tests.
2. State scope, dependencies, migration impact, risks, and rollback.
3. Make one small behavior-preserving change or one vertical feature.
4. Add success, failure, authorization, and tenant-isolation tests as relevant.
5. Run the narrow tests, then the full required checks.
6. Compare RAG/model/parser changes with the frozen baseline.
7. Update docs and plan status only when behavior is merged and verified.

Do not combine dependency upgrades, schema/tenancy changes, multimodal parsing,
and agent orchestration in one PR. Do not add a service or framework because it
is fashionable; justify it with a current need and evaluation.

## Validation

Use the checked-in lock and CI commands:

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -q
```

Add Postgres, Qdrant, storage, worker, security, evaluation, or browser tests
when the changed boundary requires them. Compilation/import success alone does
not prove routing, authorization, migration, retrieval, or runtime correctness.

## Immediate Order

1. Reproducible baseline, root uv, Ruff, locked Docker/CI.
2. Validated settings, lifespan composition, health semantics.
3. Alembic baseline and request/task database sessions.
4. Organizations, workspaces, memberships, RBAC, and tenant-safe stores.
5. Durable documents/jobs, private storage, and citation source API.
6. Async ingestion, then evaluated multimodal/routing/agent capabilities.
