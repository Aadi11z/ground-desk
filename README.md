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
- Experimental adaptive retrieval with deterministic rewrites, multi-query expansion, HyDE-style expansion, and context compression; hybrid retrieval remains the measured default.
- Metadata filters plus final reranker hooks.
- Pluggable vector-store backend with local development storage and optional Qdrant adapter.
- Gemini-backed Retrieval-Augmented Generation with citations.
- Higher-level support workflows: escalation notes, summaries, FAQ generation, knowledge-gap detection, and support-article suggestions.
- Synthetic eval-data generation plus retrieval/answer-quality metrics.
- BEIR/qrels benchmark runner that reports retrieval Recall, MRR, nDCG, MAP, no-hit rate, and latency on labelled datasets.
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
GET    /api/benchmark/summary
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

## Retrieval Benchmark Demo

The built-in sample corpus verifies application behavior; it is not evidence of
retrieval quality. For an interview demo, run GroundDesk against the labelled
BEIR NFCorpus test set in an isolated local index.

Fast baseline with no API cost or model download:

```bash
./venv/bin/python scripts/run_retrieval_benchmark.py \
  --download nfcorpus \
  --modes sparse,hybrid,adaptive \
  --embedding-provider hashing \
  --embedding-model hashing \
  --output results/nfcorpus_fast.json \
  --report results/nfcorpus_fast.md
```

Stronger semantic comparison using a local embedding model:

```bash
./venv/bin/python scripts/run_retrieval_benchmark.py \
  --dataset-dir benchmarks/data/nfcorpus \
  --modes dense,hybrid,adaptive \
  --embedding-provider sentence-transformers \
  --embedding-model BAAI/bge-small-en-v1.5 \
  --output results/nfcorpus_bge.json \
  --report benchmarks/reports/nfcorpus_bge.md \
  --publish-summary benchmarks/reports/nfcorpus_bge.json
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
./venv/bin/python scripts/run_retrieval_benchmark.py \
  --dataset-dir benchmarks/data/nfcorpus \
  --sample-queries 5 \
  --sample-corpus-documents 150 \
  --sample-seed 42 \
  --modes dense,hybrid,adaptive \
  --embedding-provider gemini \
  --embedding-model gemini-embedding-2 \
  --embedding-dimensions 768,1536,3072 \
  --allow-gemini-corpus-embedding \
  --output results/nfcorpus_gemini_slice.json \
  --report benchmarks/reports/nfcorpus_gemini_slice.md \
  --publish-summary benchmarks/reports/nfcorpus_gemini_slice.json
```

This slice verifies Gemini Embedding 2 and MRL-vector integration under free-tier
constraints; it must not be described as full-corpus benchmark performance.

## Project Layout

```text
app/
  core/                 Shared config, schemas, and safety helpers
  ingestion/            Loaders, chunking, quality controls, ingestion service
  retrieval/            Embeddings, lexical search, fusion, vector-store backends
  generation/           RAG agent and LLM providers
  evals/                Golden-set and labelled retrieval evaluation
  interfaces/           FastAPI app and Gradio UI
sample_corpus/          Built-in demo support docs
scripts/                Operational helpers such as Qdrant migration
benchmarks/data/        Downloaded evaluation corpora (ignored by git)
benchmarks/reports/     Reviewed benchmark artifacts displayed in the demo
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
