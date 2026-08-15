UV ?= uv
PYTHON ?= $(UV) run python
HOST ?= 127.0.0.1
PORT ?= 8000
OFFLINE_DATA_DIR ?= data/local-offline
GEMINI_DATA_DIR ?= data/local-gemini
LOCAL_ADMIN_KEY ?= local-admin-secret

.DEFAULT_GOAL := help

.PHONY: \
	help sync check lint format format-check test \
	run-local run-gemini reset-local reset-gemini \
	clean-local clean-gemini dev local local-fresh local-gemini local-gemini-fresh

help:
	@printf '%s\n' \
		"GroundDesk commands:" \
		"  make run-local       Start the offline local product (default development mode)." \
		"  make run-gemini      Start locally with Gemini; requires GEMINI_API_KEY." \
		"  make reset-local     Delete offline local data, then start a fresh offline product." \
		"  make reset-gemini    Delete Gemini local data, then start a fresh Gemini product." \
		"  make clean-local     Delete offline local data only." \
		"  make clean-gemini    Delete Gemini local data only." \
		"  make check           Run lint, format check, and tests." \
		"  make format          Apply Ruff formatting." \
		"  make dev             Start with your current environment configuration." \
		"" \
		"Set HOST=127.0.0.1 and PORT=8000 to override the local server address."

run-local: sync
	@echo "Starting GroundDesk locally with offline providers at http://$(HOST):$(PORT)/"
	@echo "Open http://$(HOST):$(PORT)/ and use the Documents tab to upload files."
	AUTH_MODE=demo \
	DEFAULT_WORKSPACE_ID=demo \
	DATA_DIR=$(OFFLINE_DATA_DIR) \
	SAMPLE_DIR=sample_corpus \
	VECTOR_STORE=local \
	PERSISTENCE_BACKEND=database \
	DATABASE_URL=sqlite:///$(OFFLINE_DATA_DIR)/grounddesk.db \
	DATABASE_AUTO_CREATE=true \
	EMBEDDING_PROVIDER=hashing \
	EMBEDDING_MODEL=hashing \
	EMBEDDING_DIMENSIONS=384 \
	GENERATION_PROVIDER=template \
	ADMIN_API_KEY=$(LOCAL_ADMIN_KEY) \
	$(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

clean-local:
	@echo "Removing offline local data at $(OFFLINE_DATA_DIR)."
	rm -rf "$(OFFLINE_DATA_DIR)"

reset-local: clean-local
	$(MAKE) run-local HOST="$(HOST)" PORT="$(PORT)" LOCAL_ADMIN_KEY="$(LOCAL_ADMIN_KEY)"

run-gemini: sync
	@echo "Starting GroundDesk locally with Gemini at http://$(HOST):$(PORT)/"
	@echo "GEMINI_API_KEY must be set in .env or the shell."
	@echo "Open http://$(HOST):$(PORT)/ and use the Documents tab to upload files."
	AUTH_MODE=demo \
	DEFAULT_WORKSPACE_ID=demo \
	DATA_DIR=$(GEMINI_DATA_DIR) \
	SAMPLE_DIR=sample_corpus \
	VECTOR_STORE=local \
	PERSISTENCE_BACKEND=database \
	DATABASE_URL=sqlite:///$(GEMINI_DATA_DIR)/grounddesk.db \
	DATABASE_AUTO_CREATE=true \
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

clean-gemini:
	@echo "Removing Gemini local data at $(GEMINI_DATA_DIR)."
	rm -rf "$(GEMINI_DATA_DIR)"

reset-gemini: clean-gemini
	$(MAKE) run-gemini HOST="$(HOST)" PORT="$(PORT)" LOCAL_ADMIN_KEY="$(LOCAL_ADMIN_KEY)"

# Backward-compatible aliases for the original local commands.
local: run-local

local-fresh: reset-local

local-gemini: run-gemini

local-gemini-fresh: reset-gemini

sync:
	@command -v "$(UV)" >/dev/null 2>&1 || (echo "uv is required. Install it from https://docs.astral.sh/uv/" && exit 1)
	$(UV) sync --locked

dev: sync
	$(UV) run --locked uvicorn app.main:app --reload

lint: sync
	$(UV) run --locked ruff check .

format: sync
	$(UV) run --locked ruff format .

format-check: sync
	$(UV) run --locked ruff format --check .

test: sync
	$(UV) run --locked pytest -q

check: lint format-check test
