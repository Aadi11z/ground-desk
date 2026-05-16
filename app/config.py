from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "SupportIQ"
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    sample_dir: Path = Path(os.getenv("DATA_DIR", "sample_corpus"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    default_provider: str = os.getenv("DEFAULT_PROVIDER", "template")
    default_model: str = os.getenv("SUPPORTIQ_DEFAULT_MODEL", "")
    max_context_chunks: int = int(os.getenv("SUPPORTIQ_MAX_CONTEXT_CHUNKS", "5"))
    min_confidence: float = float(os.getenv("SUPPORTIQ_MIN_CONFIDENCE", "0.35"))

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"


settings = Settings()
