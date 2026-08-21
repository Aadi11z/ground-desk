UV ?= uv
PYTHON ?= $(UV) run python
HOST ?= 127.0.0.1
PORT ?= 8000

.DEFAULT_GOAL := help

.PHONY: \
	help sync check lint format format-check test frontend-install frontend-dev frontend-build frontend-test frontend-check \
	dev

help:
	@printf '%s\n' \
		"GroundDesk commands:" \
		"  make dev             Start the Supabase-backed API using your .env configuration." \
		"  make check           Run lint, format check, and tests." \
		"  make frontend-dev    Start the React/Vite interface at http://127.0.0.1:5173." \
		"  make format          Apply Ruff formatting." \
		"" \
		"Run make frontend-dev in another terminal, then open http://127.0.0.1:5173."

sync:
	@command -v "$(UV)" >/dev/null 2>&1 || (echo "uv is required. Install it from https://docs.astral.sh/uv/" && exit 1)
	$(UV) sync --locked

api: sync
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

frontend-install:
	npm --prefix frontend ci

frontend-dev: frontend-install
	npm --prefix frontend run dev -- --host $(HOST)

frontend-build: frontend-install
	npm --prefix frontend run build

frontend-test: frontend-install
	npm --prefix frontend run test

frontend-check: frontend-build frontend-test
