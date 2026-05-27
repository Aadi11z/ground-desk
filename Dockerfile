FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/grounddesk_data

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY sample_corpus ./sample_corpus
COPY benchmarks/datasets ./benchmarks/datasets
COPY benchmarks/reports ./benchmarks/reports
COPY run_demo.py .

EXPOSE 8080

CMD ["uvicorn", "app.interfaces.api:app", "--host", "0.0.0.0", "--port", "8080"]
