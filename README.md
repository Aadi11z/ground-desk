# GroundDesk

GroundDesk is a B2B product built for organization's and their internal teams for their particular user base. It ingests support documentation, retrieves relevant evidence, generates cited answers, drafts customer-support replies, and escalates requests whose evidence is missing, ambiguous, or insufficient.

## Quickstart

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q

cp .env.example .env
# edit .env and set GEMINI_API_KEY

docker compose up -d qdrant
curl -X DELETE http://localhost:6333/collections/grounddesk_chunks
rm -rf data/index data/documents

python -m uvicorn app.interfaces.api:app --reload
```

Open the demo:

```text
http://localhost:8000
```

The app automatically indexes the bundled documents in `sample_corpus/` when no local index exists.
The normal-user product UI is available at `http://localhost:8000`. A local
Gradio management UI can be enabled explicitly with `ENABLE_GRADIO_ADMIN=true`;
do not expose it publicly while knowledge-management authorization remains
temporary.

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
- PostgreSQL-compatible conversation, answer-trace, and feedback persistence,
  with JSONL fallback for zero-setup local demonstrations.
- Bounded multi-turn context for continued threads, with prior conversation
  separated from factual retrieved evidence.
- Optional Supabase Auth-backed workspace membership enforcement; anonymous
  portfolio-demo users are confined to the fixed `demo` workspace.
- Gemini generation using the server-side `GEMINI_API_KEY`, with a configurable
  Flash-Lite fallback for primary-model quota or availability failures.
- Workspace-scoped retrieval enforced from public-demo scope or authenticated
  Supabase workspace membership.
- Disabled-by-default management endpoints; temporary API-key access is
  available for local administration until proper authentication is added.
- Deterministic template generation for offline tests and eval scaffolding.
- Deterministic hashing embeddings for offline tests and demos.
- Optional public pretrained embeddings with `BAAI/bge-small-en-v1.5`.
- FastAPI backend with OpenAPI docs.
- Optional local Gradio management UI mounted at `/demo` only when enabled.
- Golden-set evaluation endpoint.
- Product-specific labelled support evaluation for citations, escalation and
  follow-up behavior.
- Dockerfile and GCP Cloud Run deployment guide.

## API Surface

```text
GET    /api/health
GET    /api/benchmark/summary
GET    /api/client-config
GET    /api/documents
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
GET    /demo
```

Example:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: demo" \
  -d '{
    "question": "How long do password reset emails take?",
    "top_k": 5,
    "draft_ticket_reply": true
  }'
```

Management endpoints are disabled when `ADMIN_API_KEY` is unset. For local
maintenance only, set it and send `X-Admin-API-Key` on management requests.

## Interaction Persistence

The default local setup continues to write interaction state to JSONL:

```dotenv
PERSISTENCE_BACKEND=jsonl
FEEDBACK_PATH=data/feedback.jsonl
CHAT_HISTORY_PATH=data/chat_history.jsonl
```

For a durable hosted implementation, use PostgreSQL or Supabase PostgreSQL:

1. Apply [`migrations/0001_product_interactions.sql`](migrations/0001_product_interactions.sql)
   and [`migrations/0003_evidence_status.sql`](migrations/0003_evidence_status.sql)
   in the target database (`0002` is also required for authenticated workspace mode).
2. Set server-side deployment variables:

```dotenv
PERSISTENCE_BACKEND=database
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
DATABASE_AUTO_CREATE=false
```

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
The default deployed portfolio mode is intentionally anonymous and fixed to
the `demo` workspace; callers cannot switch to a different workspace through
`X-Workspace-ID`.
`GET /api/health` reports degraded status if configured database tables are not
reachable, which makes a missed migration visible during deployment validation.
After applying the migrations, verify a Supabase PostgreSQL connection with:

```bash
./venv/bin/python scripts/check_database_setup.py \
  --workspace-id demo \
  --workspace-name "GroundDesk Demo"
```

## Authentication And Workspaces

There are two normal-user modes:

```dotenv
# Public portfolio demo: users can access only DEFAULT_WORKSPACE_ID=demo.
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

1. Create a Supabase project and enable the desired sign-in provider.
2. Apply both migrations in order:

```text
migrations/0001_product_interactions.sql
migrations/0002_auth_workspace_membership.sql
migrations/0003_evidence_status.sql
```

3. Insert each organization and authorized user membership in Supabase SQL:

```sql
insert into workspaces (id, name) values ('acme', 'Acme Support');

insert into workspace_members (workspace_id, user_id, role)
values ('acme', '<supabase-auth-user-uuid>', 'member');
```

4. A signed-in client supplies:

```http
Authorization: Bearer <supabase-access-token>
X-Workspace-ID: acme
```

FastAPI validates the token through Supabase Auth, verifies membership in
PostgreSQL, and only then applies the workspace filter to retrieval. The
frontend now supports email/password sign-in, refreshable browser sessions,
authorized workspace selection, personal saved-thread display, and
answer-feedback submission.

Use `AUTH_MODE=demo` for the public interview demo if you do not yet want to
provision user accounts. Enable `AUTH_MODE=supabase` once the migrations and
at least one `workspace_members` record exist.

## Retrieval Benchmark Demo

The built-in sample corpus verifies application behavior; it is not evidence of
retrieval quality. For an interview demo, run GroundDesk against the labelled
BEIR NFCorpus test set in an isolated local index.

Fast baseline with no API cost or model download:

```bash
./venv/bin/python scripts/run_retrieval_benchmark.py --download nfcorpus --modes sparse,hybrid,adaptive --embedding-provider hashing --embedding-model hashing --output results/nfcorpus_fast.json --report results/nfcorpus_fast.md
```

Stronger semantic comparison using a local embedding model:

```bash
./venv/bin/python scripts/run_retrieval_benchmark.py --dataset-dir benchmarks/data/nfcorpus --modes dense,hybrid,adaptive --embedding-provider sentence-transformers --embedding-model BAAI/bge-small-en-v1.5 --output results/nfcorpus_bge.json --report benchmarks/reports/nfcorpus_bge.md --publish-summary benchmarks/reports/nfcorpus_bge.json
```

The first run downloads the public NFCorpus archive; the second may download
the BGE model once. The generated Markdown scorecard is suitable for showing:

- the corpus and labelled query count;
- retrieval performance by strategy (`Recall@5`, `MRR@10`, `nDCG@10`, `MAP@10`);
- no-hit rate and p50/p95 query latency;
- the exact embedding backend and index size.

These metrics validate retrieval ranking only. They do not yet validate answer
faithfulness or calibrated confidence.

The deployed demo exposes a reviewed benchmark artifact through
`GET /api/benchmark/summary` and renders its hybrid-retrieval result in the UI.
The full JSON output remains ignored under `results/` for local failure analysis;
review and commit the compact `benchmarks/reports/` artifacts before deployment.

The reviewed NFCorpus result selects `hybrid` as the deployed retrieval default:
the current adaptive-rules strategy is retained for experiments because it did
not improve the labelled benchmark.

For a quota-controlled verification of the live Gemini embedding path:

```bash
./venv/bin/python scripts/run_retrieval_benchmark.py --dataset-dir benchmarks/data/nfcorpus --sample-queries 5 --sample-corpus-documents 150 --sample-seed 42 --modes dense,hybrid,adaptive --embedding-provider gemini --embedding-model gemini-embedding-2 --embedding-dimensions 768,1536,3072 --allow-gemini-corpus-embedding --output results/nfcorpus_gemini_slice.json --report benchmarks/reports/nfcorpus_gemini_slice.md --publish-summary benchmarks/reports/nfcorpus_gemini_slice.json
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
./venv/bin/python scripts/run_support_evaluation.py --modes dense,hybrid,adaptive --embedding-provider hashing --embedding-model hashing --generation-provider template --top-k 3 --output results/grounddesk_support_hashing.json --report results/grounddesk_support_hashing.md
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
./venv/bin/python scripts/run_support_evaluation.py \
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
./venv/bin/python scripts/run_support_evaluation.py --modes planned --query-planner-provider gemini --embedding-provider gemini --embedding-model gemini-embedding-2 --embedding-dimensions 768,1536,3072 --generation-provider template --allow-provider-api-calls --output results/grounddesk_support_planned.json --report results/grounddesk_support_planned.md
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
  core/                 Shared config, schemas, safety and persistence repositories
  ingestion/            Loaders, chunking, quality controls, ingestion service
  retrieval/            Embeddings, lexical search, fusion, vector-store backends
  generation/           RAG agent and LLM providers
  evals/                Golden-set and labelled retrieval evaluation
  interfaces/           FastAPI app and Gradio UI
sample_corpus/          Built-in demo support docs
scripts/                Operational helpers such as Qdrant migration
benchmarks/data/        Downloaded evaluation corpora (ignored by git)
benchmarks/datasets/    Product-specific labelled evaluation cases
benchmarks/reports/     Reviewed benchmark artifacts displayed in the demo
tests/                  Unit tests
migrations/             PostgreSQL schema migrations for durable product state
docs/                   Project docs and roadmap
presentation/           Generated interview/demo slide deck
```

## Documentation

- [Implementation guide](docs/IMPLEMENTATION.md)
- [Product roadmap](docs/PRODUCT_ROADMAP.md)
- [Deployment and operations](docs/DEPLOYMENT.md)
- [Two-hour demo runbook](docs/DEMO_RUNBOOK.md)

Generate the black-and-white interview deck:

```bash
./venv/bin/python -m pip install python-pptx
./venv/bin/python scripts/create_demo_deck.py
```

## Deploy

Build locally:

```bash
docker build -t ground-desk .
docker run --rm -p 8080:8080 ground-desk
```

Deploy to Cloud Run using [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
