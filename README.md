# GroundDesk

GroundDesk is an end-to-end Generative AI support-agent project built to show the practical skills expected from an AI engineer: RAG, LLM API integration, structured generation, evals, safety checks, FastAPI, Gradio, Docker, CI, and Cloud Run deployment.

It ingests support documentation, retrieves relevant evidence, generates cited answers, drafts customer-support replies, flags low-confidence cases for escalation, and exposes both production APIs and a portfolio-friendly web demo.

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
The Gradio admin/demo UI remains available at `http://localhost:8000/demo`.

## Core Features

- Structured support-document ingestion for Markdown, TXT, PDF, and URLs.
- Stable document IDs, versioned manifests, and provenance-rich chunks.
- Gemini-compatible MRL retrieval with named dense vector fields and coarse-to-fine reranking.
- Hybrid retrieval with dense semantic search, BM25-style lexical search, and reciprocal-rank fusion.
- Adaptive retrieval with query analysis, deterministic rewrites, multi-query expansion, HyDE-style expansion, and context compression.
- Metadata filters plus final reranker hooks.
- Pluggable vector-store backend with local development storage and optional Qdrant adapter.
- Gemini-backed Retrieval-Augmented Generation with citations.
- Higher-level support workflows: escalation notes, summaries, FAQ generation, knowledge-gap detection, and support-article suggestions.
- Synthetic eval-data generation plus retrieval/answer-quality metrics.
- Local chat-history, feedback, analytics, and object-storage scaffolding.
- Gemini-only generation using the server-side `GEMINI_API_KEY`.
- Workspace-scoped retrieval with `X-Workspace-ID`.
- Admin API-key protection for ingestion, delete, eval, history, analytics, and workflow endpoints.
- Deterministic template generation for offline tests and eval scaffolding.
- Deterministic hashing embeddings for offline tests and demos.
- Optional public pretrained embeddings with `BAAI/bge-small-en-v1.5`.
- FastAPI backend with OpenAPI docs.
- Gradio demo mounted at `/demo`.
- Golden-set evaluation endpoint.
- Dockerfile and GCP Cloud Run deployment guide.

## API Surface

```text
GET    /api/health
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
POST   /api/workflows/escalation-note
POST   /api/workflows/conversation-summary
POST   /api/workflows/knowledge-gap
POST   /api/workflows/support-article
GET    /api/workflows/documents/{document_id}/summary
GET    /api/workflows/documents/{document_id}/faq
GET    /api/workflows/documents/{document_id}/changelog-summary
POST   /api/feedback
GET    /api/history
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

Admin endpoints use `X-Admin-API-Key` when `ADMIN_API_KEY` is set.

## Project Layout

```text
app/
  core/                 Shared config, schemas, and safety helpers
  ingestion/            Loaders, chunking, quality controls, ingestion service
  retrieval/            Embeddings, lexical search, fusion, vector-store backends
  generation/           RAG agent and LLM providers
  evals/                Golden-set evaluation
  interfaces/           FastAPI app and Gradio UI
sample_corpus/          Built-in demo support docs
scripts/                Operational helpers such as Qdrant migration
tests/                  Unit tests
docs/                   Project docs and roadmap
```

## Documentation

- [Implementation guide](docs/IMPLEMENTATION.md)
- [Product roadmap](docs/PRODUCT_ROADMAP.md)
- [Deployment and operations](docs/DEPLOYMENT.md)

## Deploy

Build locally:

```bash
docker build -t ground-desk .
docker run --rm -p 8080:8080 ground-desk
```

Deploy to Cloud Run using [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
