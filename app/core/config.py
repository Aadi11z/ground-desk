from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    app_name: str = "GroundDesk"
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    sample_dir: Path = Path(_env("GROUNDDESK_SAMPLE_DIR", "sample_corpus"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    embedding_provider: str = _env("GROUNDDESK_EMBEDDING_PROVIDER", "auto")
    embedding_dimensions: tuple[int, ...] = tuple(
        int(value.strip())
        for value in _env(
            "GROUNDDESK_EMBEDDING_DIMENSIONS",
            "768,1536,3072",
        ).split(",")
        if value.strip()
    )
    generation_provider: str = _env("GROUNDDESK_GENERATION_PROVIDER", "gemini")
    generation_model: str = _env("GROUNDDESK_GENERATION_MODEL", "gemini-2.5-flash")
    max_context_chunks: int = int(_env("GROUNDDESK_MAX_CONTEXT_CHUNKS", "5"))
    min_confidence: float = float(_env("GROUNDDESK_MIN_CONFIDENCE", "0.35"))
    retrieval_mode: str = _env("GROUNDDESK_RETRIEVAL_MODE", "adaptive")
    dense_candidate_k: int = int(_env("GROUNDDESK_DENSE_CANDIDATE_K", "20"))
    sparse_candidate_k: int = int(_env("GROUNDDESK_SPARSE_CANDIDATE_K", "20"))
    coarse_candidate_k: int = int(_env("GROUNDDESK_COARSE_CANDIDATE_K", "100"))
    reciprocal_rank_k: int = int(_env("GROUNDDESK_RRF_K", "60"))
    dense_rrf_weight: float = float(_env("GROUNDDESK_DENSE_RRF_WEIGHT", "1.0"))
    sparse_rrf_weight: float = float(_env("GROUNDDESK_SPARSE_RRF_WEIGHT", "1.0"))
    adaptive_retrieval_enabled: bool = _env(
        "GROUNDDESK_ADAPTIVE_RETRIEVAL",
        "true",
    ).lower() == "true"
    multi_query_limit: int = int(_env("GROUNDDESK_MULTI_QUERY_LIMIT", "3"))
    context_max_sentences: int = int(_env("GROUNDDESK_CONTEXT_MAX_SENTENCES", "3"))
    final_reranker: str = _env("GROUNDDESK_FINAL_RERANKER", "lexical")
    cross_encoder_model: str = _env("GROUNDDESK_CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    vector_store_backend: str = _env("GROUNDDESK_VECTOR_STORE", "local")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "grounddesk_chunks")
    feedback_path: Path = Path(_env("GROUNDDESK_FEEDBACK_PATH", "data/feedback.jsonl"))
    chat_history_path: Path = Path(
        _env(
            "GROUNDDESK_CHAT_HISTORY_PATH",
            "data/chat_history.jsonl",
        )
    )

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"


settings = Settings()
