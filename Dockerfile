FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/grounddesk_data
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app
COPY sample_corpus ./sample_corpus
COPY benchmarks/datasets ./benchmarks/datasets
COPY benchmarks/reports ./benchmarks/reports
COPY run_demo.py .

RUN uv sync --locked --no-dev

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
