from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "SupportIQ"
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    sample_dir: Path = Path(os.getenv("SUPPORTIQ_SAMPLE_DIR", "sample_corpus"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    embedding_provider: str = os.getenv("SUPPORTIQ_EMBEDDING_PROVIDER", "auto")
    embedding_dimensions: tuple[int, ...] = tuple(
        int(value.strip())
        for value in os.getenv("SUPPORTIQ_EMBEDDING_DIMENSIONS", "768,1536,3072").split(",")
        if value.strip()
    )
    default_provider: str = os.getenv("DEFAULT_PROVIDER", "template")
    default_model: str = os.getenv("SUPPORTIQ_DEFAULT_MODEL", "")
    max_context_chunks: int = int(os.getenv("SUPPORTIQ_MAX_CONTEXT_CHUNKS", "5"))
    min_confidence: float = float(os.getenv("SUPPORTIQ_MIN_CONFIDENCE", "0.35"))
    retrieval_mode: str = os.getenv("SUPPORTIQ_RETRIEVAL_MODE", "adaptive")
    dense_candidate_k: int = int(os.getenv("SUPPORTIQ_DENSE_CANDIDATE_K", "20"))
    sparse_candidate_k: int = int(os.getenv("SUPPORTIQ_SPARSE_CANDIDATE_K", "20"))
    coarse_candidate_k: int = int(os.getenv("SUPPORTIQ_COARSE_CANDIDATE_K", "100"))
    reciprocal_rank_k: int = int(os.getenv("SUPPORTIQ_RRF_K", "60"))
    dense_rrf_weight: float = float(os.getenv("SUPPORTIQ_DENSE_RRF_WEIGHT", "1.0"))
    sparse_rrf_weight: float = float(os.getenv("SUPPORTIQ_SPARSE_RRF_WEIGHT", "1.0"))
    adaptive_retrieval_enabled: bool = os.getenv("SUPPORTIQ_ADAPTIVE_RETRIEVAL", "true").lower() == "true"
    multi_query_limit: int = int(os.getenv("SUPPORTIQ_MULTI_QUERY_LIMIT", "3"))
    context_max_sentences: int = int(os.getenv("SUPPORTIQ_CONTEXT_MAX_SENTENCES", "3"))
    final_reranker: str = os.getenv("SUPPORTIQ_FINAL_RERANKER", "lexical")
    cross_encoder_model: str = os.getenv(
        "SUPPORTIQ_CROSS_ENCODER_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
    )
    vector_store_backend: str = os.getenv("SUPPORTIQ_VECTOR_STORE", "local")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "supportiq_chunks")
    feedback_path: Path = Path(os.getenv("SUPPORTIQ_FEEDBACK_PATH", "data/feedback.jsonl"))
    chat_history_path: Path = Path(os.getenv("SUPPORTIQ_CHAT_HISTORY_PATH", "data/chat_history.jsonl"))

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"


settings = Settings()
