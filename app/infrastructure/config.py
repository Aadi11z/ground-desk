"""Validated configuration loaded from the process environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PositiveInt = Annotated[int, Field(ge=1)]
NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]


class Settings(BaseSettings):
    """GroundDesk runtime configuration.

    Environment values are parsed once at startup. Production rejects unsafe
    fallback adapters before the application accepts traffic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        enable_decoding=False,
        extra="ignore",
        frozen=True,
        populate_by_name=True,
        validate_default=True,
    )

    app_name: str = "GroundDesk"
    app_environment: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    data_dir: Path = Path("data")
    corpus_dir: Path = Field(default=Path("corpus"), validation_alias="CORPUS_DIR")

    embedding_model: str = "gemini-embedding-2"
    embedding_provider: str = "auto"
    gemini_embedding_max_attempts: PositiveInt = 4
    gemini_embedding_retry_base_seconds: NonNegativeFloat = 2.0
    embedding_dimensions: tuple[PositiveInt, ...] = (768, 1536, 3072)

    generation_provider: str = "gemini"
    generation_model: str = "gemini-2.5-flash"
    generation_fallback_models: tuple[str, ...] = ("gemini-2.5-flash-lite",)
    gemini_generation_max_attempts: PositiveInt = 4
    gemini_generation_retry_base_seconds: NonNegativeFloat = 2.0
    gemini_generation_request_delay_seconds: NonNegativeFloat = 0.0
    gemini_api_key: SecretStr | None = None
    conversation_context_turns: PositiveInt = 4

    supabase_url: AnyHttpUrl | None = None
    supabase_publishable_key: str | None = None
    supabase_jwt_audience: str = "authenticated"
    admin_api_key: SecretStr | None = None

    max_context_chunks: PositiveInt = 5
    retrieval_mode: Literal["dense", "sparse", "hybrid", "adaptive", "planned"] = (
        "hybrid"
    )
    dense_candidate_k: PositiveInt = 20
    sparse_candidate_k: PositiveInt = 20
    coarse_candidate_k: PositiveInt = 100
    reciprocal_rank_k: PositiveInt = Field(default=60, validation_alias="RRF_K")
    dense_rrf_weight: NonNegativeFloat = 1.0
    sparse_rrf_weight: NonNegativeFloat = 1.0
    adaptive_retrieval_enabled: bool = Field(
        default=False, validation_alias="ADAPTIVE_RETRIEVAL"
    )
    multi_query_limit: PositiveInt = 3
    query_planner_provider: str = "off"
    query_planner_model: str = "gemini-2.5-flash"
    context_max_sentences: PositiveInt = 3
    final_reranker: str = "lexical"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    vector_store_backend: Literal["local", "qdrant"] = Field(
        default="local", validation_alias="VECTOR_STORE"
    )
    qdrant_url: AnyHttpUrl = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "grounddesk_chunks"

    persistence_backend: Literal["database"] = "database"
    database_url: str = ""
    database_auto_create: bool = False
    database_pool_size: PositiveInt = 5
    database_max_overflow: NonNegativeInt = 0
    database_pool_timeout_seconds: PositiveInt = 5
    database_pool_recycle_seconds: PositiveInt = 300
    database_prepared_statements: bool = False
    benchmark_report_path: Path = Path("benchmarks/reports/nfcorpus_bge.json")
    support_eval_dataset_path: Path = Path(
        "benchmarks/datasets/grounddesk_support_v1.json"
    )

    @field_validator("embedding_dimensions", mode="before")
    @classmethod
    def parse_embedding_dimensions(
        cls, value: str | tuple[int, ...] | list[int]
    ) -> tuple[int, ...]:
        if isinstance(value, str):
            values = tuple(item.strip() for item in value.split(",") if item.strip())
            if not values:
                raise ValueError(
                    "EMBEDDING_DIMENSIONS must contain at least one value."
                )
            return tuple(int(item) for item in values)
        return tuple(value)

    @field_validator("generation_fallback_models", mode="before")
    @classmethod
    def parse_generation_fallback_models(
        cls, value: str | tuple[str, ...] | list[str]
    ) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return tuple(value)

    @field_validator("supabase_publishable_key", mode="before")
    @classmethod
    def normalize_optional_blank_strings(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @field_validator("supabase_url", mode="before")
    @classmethod
    def normalize_optional_url(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @field_validator("admin_api_key", "gemini_api_key", "qdrant_api_key", mode="before")
    @classmethod
    def normalize_optional_secrets(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str | None) -> str:
        return value.strip() if isinstance(value, str) else ""

    @model_validator(mode="after")
    def validate_production_configuration(self) -> Settings:
        if self.app_environment != "production":
            return self

        missing: list[str] = []
        if self.persistence_backend != "database":
            missing.append("PERSISTENCE_BACKEND=database")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if self.supabase_url is None:
            missing.append("SUPABASE_URL")
        if not self.supabase_publishable_key:
            missing.append("SUPABASE_PUBLISHABLE_KEY")
        if self.vector_store_backend != "qdrant":
            missing.append("VECTOR_STORE=qdrant")
        if self.database_auto_create:
            missing.append("DATABASE_AUTO_CREATE=false")
        if self.admin_api_key is not None:
            missing.append("ADMIN_API_KEY must be unset")
        if missing:
            raise ValueError(
                "Production configuration is incomplete or unsafe: "
                + ", ".join(missing)
            )
        return self

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def admin_api_key_value(self) -> str | None:
        return (
            self.admin_api_key.get_secret_value()
            if self.admin_api_key is not None
            else None
        )

    @property
    def qdrant_api_key_value(self) -> str | None:
        return (
            self.qdrant_api_key.get_secret_value()
            if self.qdrant_api_key is not None
            else None
        )

    @property
    def supabase_url_value(self) -> str | None:
        return str(self.supabase_url) if self.supabase_url is not None else None


@lru_cache
def get_settings() -> Settings:
    """Return the process configuration after validating its environment."""
    return Settings()


settings = get_settings()
