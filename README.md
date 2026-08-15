# GroundDesk

GroundDesk is a B2B product built for organization's and their internal teams for their particular user base. It ingests support documentation, retrieves relevant evidence, generates cited answers, drafts customer-support replies, and escalates requests whose evidence is missing, ambiguous, or insufficient.

## Quickstart

```bash
uv sync --locked
uv run --locked pytest -q

# Zero-cloud local product: local vectors, template answers, runtime upload enabled.
make run-local
```

Open the product:

```text
http://localhost:8000
```

The first screen is a login page. In local mode, select **Continue as Demo
User** to enter the seeded Demo Workspace. The workspace starts
empty: upload Markdown, TXT, or PDF documents in the Documents tab, select a
document to read its extracted text, then ask questions in the Ask tab.
`sample_corpus/` is retained only for tests and evaluations. OpenAPI
documentation is available at `http://localhost:8000/docs`.

### One-Command Local Modes

| Command | Purpose |
| --- | --- |
| `make help` | List available local development commands. |
| `make run-local` | Run without cloud services using local vector storage, hashing embeddings, and deterministic answer generation. |
| `make run-gemini` | Run locally with Gemini embeddings/generation; reads `GEMINI_API_KEY` from `.env` or the shell. |
| `make reset-local` | Delete offline local data, then start with an empty workspace. |
| `make reset-gemini` | Delete Gemini local data, then start with an empty workspace. |
| `make check` | Run Ruff linting, format checking, and the full test suite. |

The offline and Gemini commands use separate index directories so vectors
created by different embedding providers are never mixed. Both modes bind only
to `127.0.0.1` by default and persist the local Demo User, organization,
workspace, memberships, conversations, and feedback in a SQLite database.

To use Gemini locally:

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY
make run-gemini
```

Set a different host or port without editing the file:

```bash
make run-local PORT=8010
```

### Runtime Profiles

GroundDesk uses one codebase with environment-specific adapters rather than
separate product forks:

| Profile | Command/configuration | Identity and data |
| --- | --- | --- |
| Offline development/demo | `make run-local` | Fixed local user, SQLite product data, local vectors, deterministic models |
| Gemini development | `make run-gemini` | Fixed local user, separate SQLite/vector data, Gemini models |
| Automated test | `make test` or `make check` | Isolated temporary stores and deterministic providers |
| Hosted product | `APP_ENV=production`, `AUTH_MODE=supabase` | Supabase Auth, Supabase Postgres, and Qdrant; unsafe local fallbacks are rejected at startup |

Build the deployable container with `docker build -t grounddesk .`; its runtime
configuration is supplied through environment variables, so the same image can
be promoted between hosted environments.

## Core Features

- Structured support-document ingestion for Markdown, TXT, PDF, and URLs (Static, only http/https).
- Stable document IDs, versioned manifests, and provenance-rich chunks.
- Gemini-compatible MRL retrieval with named dense vector fields and coarse-to-fine reranking.
- Hybrid retrieval with dense semantic search, BM25-style lexical search, and reciprocal-rank fusion.
- Experimental adaptive retrieval with deterministic rewrites, multi-query expansion, HyDE-style expansion, and context compression; hybrid retrieval remains the measured default.
- Optional Gemini structured query planner (`RETRIEVAL_MODE=planned`) with validated JSON plans, original-query preservation, and hybrid fallback on planner failure; it remains disabled until benchmarked.
- Metadata filters plus final reranker hooks.
- Pluggable vector-store backend with local development storage and optional Qdrant adapter.
- Gemini-backed Retrieval-Augmented Generation with citations and a fail-closed evidence-sufficiency gate.
- Higher-level support workflows: escalation notes, summaries, FAQ generation, knowledge-gap detection, and support-article suggestions.
- Synthetic eval-data generation plus retrieval/answer-quality metrics.
- BEIR/qrels benchmark runner that reports retrieval Recall, MRR, nDCG, MAP, no-hit rate, and latency on labelled datasets.
- PostgreSQL-compatible profile, organization, workspace, membership,
  conversation, answer-trace, and feedback persistence, with JSONL fallback
  for limited compatibility use.
- Bounded multi-turn context for continued threads, with prior conversation
  separated from factual retrieved evidence.
- Demo User login for local development and Supabase Auth-backed workspace
  membership enforcement for hosted environments.
- Gemini generation using the server-side `GEMINI_API_KEY`, with a configurable
  Flash-Lite fallback for primary-model quota or availability failures.
- Workspace-scoped retrieval enforced from local-demo scope or authenticated
  Supabase workspace membership.
- Disabled-by-default management endpoints; temporary API-key access is
  available for local administration until proper authentication is added.
- Deterministic template generation for offline tests and eval scaffolding.
- Deterministic hashing embeddings for offline tests and demos.
- Optional public pretrained embeddings with `BAAI/bge-small-en-v1.5`.
- FastAPI backend with OpenAPI docs.
- Golden-set evaluation endpoint.
- Product-specific labelled support evaluation for citations, escalation and
  follow-up behavior.
- Dockerfile and GCP Cloud Run deployment guide.

## API Surface

```text
GET    /api/health
GET    /api/client-config
POST   /api/auth/demo-session
GET    /api/me
POST   /api/onboarding
GET    /api/documents
GET    /api/documents/{document_id}/preview
POST   /api/documents
PUT    /api/documents/{document_id}
POST   /api/documents/url
DELETE /api/documents/{document_id}
POST   /api/chat
POST   /api/evals/run
POST   /api/evals/retrieval
POST   /api/evals/answers
POST   /api/evals/synthetic
POST   /api/evals/variants
POST   /api/evals/support
POST   /api/workflows/escalation-note
POST   /api/workflows/conversation-summary
POST   /api/workflows/knowledge-gap
POST   /api/workflows/support-article
GET    /api/workflows/documents/{document_id}/summary
GET    /api/workflows/documents/{document_id}/faq
GET    /api/workflows/documents/{document_id}/changelog-summary
POST   /api/feedback
GET    /api/history
GET    /api/me/workspaces
GET    /api/analytics
GET    /
```

Example:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer grounddesk-demo-session" \
  -H "X-Workspace-ID: demo" \
  -d '{
    "question": "How long do password reset emails take?",
    "top_k": 5,
    "draft_ticket_reply": true
  }'
```

Management endpoints are disabled when `ADMIN_API_KEY` is unset. For local
maintenance only, set it and send `X-Admin-API-Key` on management requests.

## Database And Persistence

The browser never connects directly to the product tables. It sends a Supabase
access token to FastAPI; FastAPI validates the token, looks up the user's active
workspace membership, derives the workspace scope, and then calls the database
repository. This keeps company isolation in backend authorization instead of
trusting a browser-provided workspace ID.

Postgres is the production source of truth for profiles, organizations,
workspaces, memberships, conversations, answer traces, and feedback. Supabase
Auth owns passwords and login sessions. Qdrant stores rebuildable retrieval
vectors, while document bytes remain local only until the planned private
Supabase Storage migration is implemented.

The `make local` setup uses SQLite so the Demo User profile and workspace are
persisted along with interaction state. The JSONL adapter remains available for
minimal compatibility runs:

```dotenv
PERSISTENCE_BACKEND=jsonl
FEEDBACK_PATH=data/feedback.jsonl
CHAT_HISTORY_PATH=data/chat_history.jsonl
```

For a durable hosted implementation, use PostgreSQL or Supabase PostgreSQL:

1. Set server-side deployment variables:

```dotenv
PERSISTENCE_BACKEND=database
# Pooled application URL (Supavisor transaction mode for Cloud Run).
DATABASE_URL=postgresql+psycopg://<user>:<password>@<pooler-host>:6543/<database>
DATABASE_AUTO_CREATE=false
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=0
DATABASE_POOL_TIMEOUT_SECONDS=5
DATABASE_POOL_RECYCLE_SECONDS=300
DATABASE_PREPARED_STATEMENTS=false
```

The API owns one bounded SQLAlchemy engine per container and creates one session
per request. Repository operations use short transactions so database
connections are returned before retrieval or model generation waits. Bound
Cloud Run maximum instances so `max instances × (pool size + max overflow)`
stays within the database connection budget.

2. For a new database, apply the reviewed Alembic baseline with a direct/admin
   URL available only to the migration job:

```bash
DATABASE_MIGRATION_URL=postgresql+psycopg://... uv run --locked alembic upgrade head
```

   For an existing database created before Alembic, take a backup, verify the
   schema, then run `uv run --locked alembic stamp 20260807_01`, followed by
   `uv run --locked alembic upgrade head`. See
   [`alembic/README.md`](alembic/README.md); do not run the baseline upgrade
   directly on a pre-Alembic database.

The database path now persists:

- conversations and individual user/assistant messages;
- answer traces containing answers, citations, evidence-support status, the
  backward-compatible uncalibrated support score, escalation status, and the
  actual generation model used;
- feedback linked to a valid answer trace.

`POST /api/chat` now returns a `conversation_id` for future multi-turn
continuation. For a continued thread, the backend loads a bounded number of
prior stored turns under the active workspace/user boundary. Previous user
questions contextualize retrieval; sanitized prior turns are supplied to
Gemini as conversation context explicitly marked as non-evidence.
Configure the bound with `CONVERSATION_CONTEXT_TURNS` (default `4`).
The local demo mode is fixed to the `demo` workspace; callers cannot switch to
a different workspace through `X-Workspace-ID`.
Use `GET /health/live` for a dependency-free process probe and
`GET /health/ready` for validated, initialized startup state. The authenticated
`GET /internal/health/dependencies` endpoint performs bounded dependency checks
without exposing failure details.
After applying the migrations, verify a Supabase PostgreSQL connection with:

```bash
uv run --locked python scripts/check_database_setup.py \
  --workspace-id demo \
  --workspace-name "GroundDesk Demo"
```

## Authentication And Workspaces

There are two identity modes. In both modes, every active workspace member has
the same product-level `User` capabilities; differentiated roles are not
implemented.

```dotenv
# Local demo: login grants the seeded Demo User access to DEFAULT_WORKSPACE_ID=demo.
AUTH_MODE=demo
```

```dotenv
# Authenticated B2B mode: users must be Supabase workspace members.
AUTH_MODE=supabase
PERSISTENCE_BACKEND=database
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable-or-anon-client-key>
DATABASE_URL=postgresql+psycopg://...
```

To enable authenticated mode:

1. Create a Supabase project, enable email/password authentication, and set the
   application URL plus the confirmation redirect URL.
2. Apply the Alembic baseline to a new database with
   `uv run --locked alembic upgrade head`. For an existing pre-Alembic database,
   use the reviewed `stamp` procedure in [`alembic/README.md`](alembic/README.md).

3. Open GroundDesk and use **Create workspace**. After the user signs up and
   has a valid Supabase session, GroundDesk creates a profile, organization,
   first workspace, and active user membership transactionally.

4. A signed-in client supplies:

```http
Authorization: Bearer <supabase-access-token>
X-Workspace-ID: acme
```

FastAPI validates the token through Supabase Auth, verifies active membership
in PostgreSQL, and only then applies the workspace filter to retrieval. The
frontend supports email/password sign-in, workspace registration, authorized
workspace selection, document management, cited chat, and personal saved
conversation history.

Use `AUTH_MODE=demo` for the public interview demo if you do not yet want to
provision user accounts. Enable `AUTH_MODE=supabase` once migrations and the
Supabase browser configuration are ready.

## Retrieval Benchmark Demo

The built-in sample corpus verifies application behavior; it is not evidence of
retrieval quality. For an interview demo, run GroundDesk against the labelled
BEIR NFCorpus test set in an isolated local index.

Fast baseline with no API cost or model download:

```bash
uv run --locked python scripts/run_retrieval_benchmark.py --download nfcorpus --modes sparse,hybrid,adaptive --embedding-provider hashing --embedding-model hashing --output results/nfcorpus_fast.json --report results/nfcorpus_fast.md
```

Stronger semantic comparison using a local embedding model:

```bash
uv run --locked python scripts/run_retrieval_benchmark.py --dataset-dir benchmarks/data/nfcorpus --modes dense,hybrid,adaptive --embedding-provider sentence-transformers --embedding-model BAAI/bge-small-en-v1.5 --output results/nfcorpus_bge.json --report benchmarks/reports/nfcorpus_bge.md --publish-summary benchmarks/reports/nfcorpus_bge.json
```

The first run downloads the public NFCorpus archive; the second may download
the BGE model once. The generated Markdown scorecard is suitable for showing:

- the corpus and labelled query count;
- retrieval performance by strategy (`Recall@5`, `MRR@10`, `nDCG@10`, `MAP@10`);
- no-hit rate and p50/p95 query latency;
- the exact embedding backend and index size.

These metrics validate retrieval ranking only. They do not yet validate answer
faithfulness or calibrated confidence.

Benchmark reports are development artifacts and are not exposed by the product
API. The full JSON output remains ignored under `results/` for local failure
analysis; reviewed compact reports may be kept under `benchmarks/reports/`.

The reviewed NFCorpus result selects `hybrid` as the deployed retrieval default:
the current adaptive-rules strategy is retained for experiments because it did
not improve the labelled benchmark.

For a quota-controlled verification of the live Gemini embedding path:

```bash
uv run --locked python scripts/run_retrieval_benchmark.py --dataset-dir benchmarks/data/nfcorpus --sample-queries 5 --sample-corpus-documents 150 --sample-seed 42 --modes dense,hybrid,adaptive --embedding-provider gemini --embedding-model gemini-embedding-2 --embedding-dimensions 768,1536,3072 --allow-gemini-corpus-embedding --output results/nfcorpus_gemini_slice.json --report benchmarks/reports/nfcorpus_gemini_slice.md --publish-summary benchmarks/reports/nfcorpus_gemini_slice.json
```

This slice verifies Gemini Embedding 2 and MRL-vector integration under free-tier
constraints; it must not be described as full-corpus benchmark performance.

## Product-Specific Support Evaluation

The repository now includes an authored evaluation set over the bundled
GroundDesk support corpus:

```text
benchmarks/datasets/grounddesk_support_v1.json
```

It contains 21 labelled cases: direct answerable questions, unsupported or
ambiguous questions that should escalate, and follow-up questions requiring
conversation context.

Run the deterministic offline evaluation without API cost:

```bash
uv run --locked python scripts/run_support_evaluation.py --modes dense,hybrid,adaptive --embedding-provider hashing --embedding-model hashing --generation-provider template --top-k 3 --output results/grounddesk_support_hashing.json --report results/grounddesk_support_hashing.md
```

The pre-gate hashing/template run exposed that hybrid retrieval escalated only
`20.0%` of unsupported/ambiguous examples because relative fused retrieval
ranks were incorrectly being used as confidence. The implemented evidence
gate no longer accepts RRF/reranker scores as correctness probabilities. The
current offline run (`results/grounddesk_support_hashing_gated.md`) reports,
for dense/hybrid/adaptive alike: `93.8%` correct top citation, `87.5%`
expected-term coverage, `95.2%` escalation decision accuracy, `100.0%`
unsupported/ambiguous escalation, and `100.0% / 80.0%` follow-up top-citation
accuracy with / without context. One answerable case now escalates safely
because its top retrieved document is wrong.

After manually reviewing the cases, run the Gemini path:

```bash
uv run --locked python scripts/run_support_evaluation.py \
  --modes hybrid \
  --embedding-provider gemini \
  --embedding-model gemini-embedding-2 \
  --embedding-dimensions 768,1536,3072 \
  --generation-provider gemini \
  --generation-model gemini-2.5-flash \
  --generation-fallback-models gemini-2.5-flash-lite \
  --allow-provider-api-calls \
  --output results/grounddesk_support_gemini_demo_ready.json \
  --report results/grounddesk_support_gemini_demo_ready.md
```

Gemini embedding and generation calls retry temporary overload/server or
short-window rate-limit errors with bounded backoff and honor provider retry
guidance; the evaluation command also applies conservative request delays.
If `gemini-2.5-flash` is unavailable or its per-model quota is exhausted,
generation tries the configured `gemini-2.5-flash-lite` fallback and stores
the model used with the answer trace. The command writes a matching
`*.partial.json` file after each completed case. If both configured models are
unavailable, rerun the identical command to resume; use `--no-resume` only to
discard a checkpoint intentionally.

Because answer acceptance logic has changed since the earlier interrupted
Gemini run, its `*.partial.json` file is historical evidence only; do not merge
it with a new post-gate report. Use a new output filename or `--no-resume` for
the next complete run.

The labelled set requires up to 21 primary Gemini answers (unsupported cases
may now be rejected before generation). If a free-tier model
allows fewer generation requests in a quota window, a complete provider report
must be resumed after quota availability resets; retrieval-only follow-up
comparisons no longer waste additional generation requests.

After the default hybrid run is complete, the optional structured planner can
be evaluated separately. It adds one Gemini request for each evaluated query:

```bash
uv run --locked python scripts/run_support_evaluation.py --modes planned --query-planner-provider gemini --embedding-provider gemini --embedding-model gemini-embedding-2 --embedding-dimensions 768,1536,3072 --generation-provider template --allow-provider-api-calls --output results/grounddesk_support_planned.json --report results/grounddesk_support_planned.md
```

Do not deploy planned retrieval unless its labelled results improve over the
static hybrid baseline within acceptable latency and quota cost.

This small product set is a demonstration/regression benchmark, not a
customer-scale accuracy claim. Gemini output must be inspected manually before
reporting generated-answer quality.

Latest demo-ready provider run using Gemini Embedding 2 with the configured
generation fallback:

| Measure | Result |
| --- | ---: |
| Correct top citation for answerable cases | 100.0% |
| Expected answer-term coverage | 93.8% |
| Overall escalation accuracy | 85.7% |
| Unsupported/ambiguous escalation accuracy | 100.0% |

Model usage in that run was `3` Flash answers, `12` Flash-Lite fallback
answers, and `6` cases gated without generation. This validates a stable demo
path under Flash quota pressure; it is not a Flash-only benchmark.

## Project Layout

```text
app/
  core/                 Schemas, safety and persistence repositories
  infrastructure/       Validated configuration and future concrete adapters
  rag/                  Loaders, retrieval, generation and evaluation pipeline
  evals/                Golden-set and labelled retrieval evaluation
  web/                  Static product interface (HTML, CSS, JavaScript)
sample_corpus/          Built-in demo support docs
scripts/                Operational helpers such as Qdrant migration
benchmarks/data/        Downloaded evaluation corpora (ignored by git)
benchmarks/datasets/    Product-specific labelled evaluation cases
benchmarks/reports/     Reviewed retrieval benchmark artifacts
tests/                  Unit tests
alembic/                PostgreSQL migration history and archived raw-SQL reference
docs/                   Project docs and roadmap
presentation/           Generated interview/demo slide deck
```

## Documentation

- [Project plan](docs/PLAN.md)
- [Current state](docs/CURRENT_STATE.md)
- [Demo runbook](docs/DEMO_RUNBOOK.md)

Generate the black-and-white interview deck:

```bash
uv run --with python-pptx python scripts/create_demo_deck.py
```

## Deploy

Build locally:

```bash
docker build -t ground-desk .
docker run --rm -p 8080:8080 ground-desk
```

See the [production architecture plan](docs/PLAN.md) for the planned Cloud Run
and Cloudflare Pages deployment.
