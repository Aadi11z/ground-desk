from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuration Table:
    ┌────────────────────┬───────────────────────────────────────────────────────────────────┐
    │ Configuration Area │ Examples                                                          │
    ├────────────────────┼───────────────────────────────────────────────────────────────────┤
    │ data locations     │ DATA_DIR, SAMPLE_DIR, FEEDBACK_PATH, CHAT_HISTORY_PATH            │
    │ persistence        │ PERSISTENCE_BACKEND, DATABASE_URL, DATABASE_AUTO_CREATE           │
    │ embeddings         │ EMBEDDING_MODEL, EMBEDDING_PROVIDER, EMBEDDING_DIMENSIONS         │
    │ generation         │ GENERATION_PROVIDER, GENERATION_MODEL                             │
    │ retrieval          │ RETRIEVAL_MODE, candidate counts, RRF weights, reranker selection │
    │ access boundary    │ ADMIN_API_KEY, DEFAULT_WORKSPACE_ID                               │
    │ vector storage     │ VECTOR_STORE, QDRANT_URL, QDRANT_COLLECTION                       │
    │ benchmark output   │ BENCHMARK_REPORT_PATH                                             │
    └────────────────────┴───────────────────────────────────────────────────────────────────┘
    """
    app_name: str = "GroundDesk"
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    sample_dir: Path = Path(os.getenv("SAMPLE_DIR", "sample_corpus"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "auto")
    embedding_dimensions: tuple[int, ...] = tuple(
        int(value.strip())
        for value in os.getenv(
            "EMBEDDING_DIMENSIONS",
            "768,1536,3072",
        ).split(",")
        if value.strip()
    )
    generation_provider: str = os.getenv("GENERATION_PROVIDER", "gemini")
    generation_model: str = os.getenv("GENERATION_MODEL", "gemini-2.5-flash")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")
    enable_gradio_admin: bool = os.getenv("ENABLE_GRADIO_ADMIN", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    default_workspace_id: str = os.getenv("DEFAULT_WORKSPACE_ID", "demo")
    max_context_chunks: int = int(os.getenv("MAX_CONTEXT_CHUNKS", "5"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.35"))
    retrieval_mode: str = os.getenv("RETRIEVAL_MODE", "hybrid")
    dense_candidate_k: int = int(os.getenv("DENSE_CANDIDATE_K", "20"))
    sparse_candidate_k: int = int(os.getenv("SPARSE_CANDIDATE_K", "20"))
    coarse_candidate_k: int = int(os.getenv("COARSE_CANDIDATE_K", "100"))
    reciprocal_rank_k: int = int(os.getenv("RRF_K", "60"))
    dense_rrf_weight: float = float(os.getenv("DENSE_RRF_WEIGHT", "1.0"))
    sparse_rrf_weight: float = float(os.getenv("SPARSE_RRF_WEIGHT", "1.0"))
    adaptive_retrieval_enabled: bool = (
        os.getenv(
            "ADAPTIVE_RETRIEVAL",
            "false",
        ).lower()
        == "true"
    )
    multi_query_limit: int = int(os.getenv("MULTI_QUERY_LIMIT", "3"))
    context_max_sentences: int = int(os.getenv("CONTEXT_MAX_SENTENCES", "3"))
    final_reranker: str = os.getenv("FINAL_RERANKER", "lexical")
    cross_encoder_model: str = os.getenv(
        "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    vector_store_backend: str = os.getenv("VECTOR_STORE", "local")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "grounddesk_chunks")
    feedback_path: Path = Path(os.getenv("FEEDBACK_PATH", "data/feedback.jsonl"))
    chat_history_path: Path = Path(
        os.getenv(
            "CHAT_HISTORY_PATH",
            "data/chat_history.jsonl",
        )
    )
    persistence_backend: str = os.getenv("PERSISTENCE_BACKEND", "jsonl")
    database_url: str = os.getenv("DATABASE_URL", "")
    database_auto_create: bool = os.getenv("DATABASE_AUTO_CREATE", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    benchmark_report_path: Path = Path(
        os.getenv(
            "BENCHMARK_REPORT_PATH",
            "benchmarks/reports/nfcorpus_bge.json",
        )
    )

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"


settings = Settings()
