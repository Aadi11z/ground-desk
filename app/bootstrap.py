"""Application composition root for long-lived GroundDesk services."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.auth import AccessController
from app.core.persistence import ProductRepository, create_product_repository
from app.infrastructure.config import Settings
from app.infrastructure.database import DatabaseRuntime, create_database_runtime
from app.rag.generation.agent import SupportAgent
from app.rag.generation.workflows import SupportWorkflowService
from app.rag.ingestion.service import IngestionService
from app.rag.retrieval.embeddings import EmbeddingModel
from app.rag.retrieval.factory import create_vector_store
from app.rag.retrieval.vector_store import VectorStoreBackend


@dataclass
class AppServices:
    """Provider instances owned by one application lifespan."""

    embedding_model: EmbeddingModel
    vector_store: VectorStoreBackend
    ingestion_service: IngestionService
    agent: SupportAgent
    workflows: SupportWorkflowService
    product_repository: ProductRepository
    access_controller: AccessController
    database_runtime: DatabaseRuntime | None = None


def build_services(settings: Settings) -> AppServices:
    """Construct long-lived adapters after startup settings are validated."""
    embedding_model = EmbeddingModel(
        settings.embedding_model,
        provider=settings.embedding_provider,
        mrl_dimensions=settings.embedding_dimensions,
        max_attempts=settings.gemini_embedding_max_attempts,
        retry_base_seconds=settings.gemini_embedding_retry_base_seconds,
    )
    vector_store = create_vector_store(settings)
    ingestion_service = IngestionService(settings, embedding_model, vector_store)
    agent = SupportAgent(settings, embedding_model, vector_store)
    workflows = SupportWorkflowService(agent)
    database_runtime = create_database_runtime(settings)
    product_repository = create_product_repository(
        settings, database_runtime=database_runtime
    )
    if settings.auth_mode == "demo":
        product_repository.ensure_demo_identity(
            user_id=settings.demo_user_id,
            email=settings.demo_user_email,
            display_name=settings.demo_user_name,
            workspace_id=settings.default_workspace_id,
        )
    access_controller = AccessController(settings, product_repository)
    return AppServices(
        embedding_model=embedding_model,
        vector_store=vector_store,
        ingestion_service=ingestion_service,
        agent=agent,
        workflows=workflows,
        product_repository=product_repository,
        access_controller=access_controller,
        database_runtime=database_runtime,
    )
