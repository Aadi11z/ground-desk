PYTHON ?= ./venv/bin/python
HOST ?= 127.0.0.1
PORT ?= 8000
OFFLINE_DATA_DIR ?= data/local-offline
GEMINI_DATA_DIR ?= data/local-gemini
LOCAL_ADMIN_KEY ?= local-admin-secret

.DEFAULT_GOAL := local

.PHONY: local local-fresh local-gemini local-gemini-fresh check-local-venv

local: check-local-venv
	@echo "Starting GroundDesk locally with offline providers at http://$(HOST):$(PORT)/"
	@echo "Admin uploads: open /docs and use X-Admin-API-Key: $(LOCAL_ADMIN_KEY)"
	AUTH_MODE=demo \
	DEFAULT_WORKSPACE_ID=demo \
	DATA_DIR=$(OFFLINE_DATA_DIR) \
	SAMPLE_DIR=sample_corpus \
	VECTOR_STORE=local \
	PERSISTENCE_BACKEND=jsonl \
	EMBEDDING_PROVIDER=hashing \
	EMBEDDING_MODEL=hashing \
	EMBEDDING_DIMENSIONS=384 \
	GENERATION_PROVIDER=template \
	ADMIN_API_KEY=$(LOCAL_ADMIN_KEY) \
	$(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

local-fresh: check-local-venv
	@echo "Removing the offline local index and re-ingesting sample_corpus/ on startup."
	rm -rf "$(OFFLINE_DATA_DIR)"
	$(MAKE) local HOST="$(HOST)" PORT="$(PORT)" LOCAL_ADMIN_KEY="$(LOCAL_ADMIN_KEY)"

local-gemini: check-local-venv
	@echo "Starting GroundDesk locally with Gemini at http://$(HOST):$(PORT)/"
	@echo "GEMINI_API_KEY must be set in .env or the shell."
	@echo "Admin uploads: open /docs and use X-Admin-API-Key: $(LOCAL_ADMIN_KEY)"
	AUTH_MODE=demo \
	DEFAULT_WORKSPACE_ID=demo \
	DATA_DIR=$(GEMINI_DATA_DIR) \
	SAMPLE_DIR=sample_corpus \
	VECTOR_STORE=local \
	PERSISTENCE_BACKEND=jsonl \
	EMBEDDING_PROVIDER=gemini \
	EMBEDDING_MODEL=gemini-embedding-2 \
	EMBEDDING_DIMENSIONS=768,1536,3072 \
	GENERATION_PROVIDER=gemini \
	GENERATION_MODEL=gemini-2.5-flash \
	GENERATION_FALLBACK_MODELS=gemini-2.5-flash-lite \
	RETRIEVAL_MODE=hybrid \
	QUERY_PLANNER_PROVIDER=off \
	ADMIN_API_KEY=$(LOCAL_ADMIN_KEY) \
	$(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

local-gemini-fresh: check-local-venv
	@echo "Removing the Gemini local index and re-ingesting sample_corpus/ on startup."
	rm -rf "$(GEMINI_DATA_DIR)"
	$(MAKE) local-gemini HOST="$(HOST)" PORT="$(PORT)" LOCAL_ADMIN_KEY="$(LOCAL_ADMIN_KEY)"

check-local-venv:
	@test -x "$(PYTHON)" || (echo "Missing $(PYTHON). Run: python -m venv venv && ./venv/bin/python -m pip install -r requirements.txt" && exit 1)

dev: 
	uv run uvicorn app.main:app --reload

lint:
	uv run ruff check .

format:
	uv run ruff format .

test: 
	uv run pytest -q
