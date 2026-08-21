FROM python:3.14.6-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/grounddesk_data \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 grounddesk \
    && useradd --uid 10001 --gid grounddesk --create-home --shell /usr/sbin/nologin grounddesk

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY --chown=grounddesk:grounddesk app ./app
COPY --chown=grounddesk:grounddesk corpus ./corpus
COPY --chown=grounddesk:grounddesk benchmarks/datasets ./benchmarks/datasets
COPY --chown=grounddesk:grounddesk benchmarks/reports ./benchmarks/reports

RUN uv sync --locked --no-dev
RUN mkdir -p "$DATA_DIR" && chown -R grounddesk:grounddesk "$DATA_DIR"

EXPOSE 8080

USER grounddesk

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
