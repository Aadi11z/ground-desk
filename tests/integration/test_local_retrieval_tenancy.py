from __future__ import annotations

from app.core.models import ChatRequest
from app.domain.permissions import WorkspaceRole
from app.domain.tenancy import TenantScope
from app.infrastructure.config import Settings
from app.rag.generation.agent import SupportAgent
from app.rag.ingestion.loaders import LoadedDocument
from app.rag.ingestion.service import IngestionService
from app.rag.retrieval.embeddings import EmbeddingModel
from app.rag.retrieval.retriever import HybridRetriever
from app.rag.retrieval.vector_store import LocalVectorStore


def _scope(workspace_id: str) -> TenantScope:
    return TenantScope(
        workspace_id=workspace_id,
        user_id=f"{workspace_id}-owner",
        role=WorkspaceRole.OWNER,
    )


def _services(
    tmp_path,
    *,
    retrieval_mode: str = "hybrid",
):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        corpus_dir=tmp_path / "corpus",
        embedding_provider="hashing",
        embedding_model="hashing",
        embedding_dimensions=(384,),
        generation_provider="template",
        retrieval_mode=retrieval_mode,
    )
    embeddings = EmbeddingModel("hashing")
    store = LocalVectorStore(settings.index_dir)
    return settings, store, IngestionService(settings, embeddings, store), embeddings


def _ingest(ingestion, scope: TenantScope, source_id: str, text: str):
    return ingestion.ingest_loaded(
        scope,
        LoadedDocument(
            title=source_id,
            text=text,
            source_type="txt",
            source=f"{source_id}.txt",
            source_id=f"memory:{source_id}",
        ),
    )


def test_local_store_list_get_count_and_delete_are_workspace_scoped(tmp_path):
    _, store, ingestion, _ = _services(tmp_path)
    alpha = _scope("alpha")
    beta = _scope("beta")
    alpha_document = _ingest(ingestion, alpha, "alpha-guide", "Alpha reset code 7412.")
    beta_document = _ingest(ingestion, beta, "beta-guide", "Beta reset code 8844.")

    assert store.count_chunks(alpha) == 1
    assert store.list_documents(alpha)[0].document_id == alpha_document.document_id
    assert store.get_document(beta, alpha_document.document_id) is None
    assert store.delete_document(beta, alpha_document.document_id) == 0
    assert store.get_document(alpha, alpha_document.document_id) is not None

    assert store.delete_document(alpha, alpha_document.document_id) == 1
    assert store.get_document(beta, beta_document.document_id) is not None


def test_same_source_id_is_namespaced_by_workspace(tmp_path):
    _, store, ingestion, _ = _services(tmp_path)
    alpha = _scope("alpha")
    beta = _scope("beta")

    alpha_document = _ingest(ingestion, alpha, "shared-guide", "Alpha policy.")
    beta_document = _ingest(ingestion, beta, "shared-guide", "Beta policy.")

    assert alpha_document.document_id != beta_document.document_id
    assert store.get_document(alpha, alpha_document.document_id) is not None
    assert store.get_document(beta, beta_document.document_id) is not None
    assert store.get_document(alpha, beta_document.document_id) is None
    assert store.get_document(beta, alpha_document.document_id) is None


def test_sparse_candidates_are_partitioned_before_bm25_scoring(tmp_path):
    settings, _, ingestion, embeddings = _services(tmp_path, retrieval_mode="sparse")
    alpha = _scope("alpha")
    beta = _scope("beta")
    alpha_document = _ingest(
        ingestion,
        alpha,
        "alpha-guide",
        "The glacier recovery procedure uses token ALPHA-77.",
    )
    for index in range(12):
        _ingest(
            ingestion,
            beta,
            f"beta-{index}",
            "The glacier recovery procedure uses a beta-only operational token.",
        )

    retriever = HybridRetriever(settings, ingestion.store, embeddings=embeddings)
    vectors = embeddings.encode_queries(["glacier recovery procedure"])
    results = retriever.retrieve(alpha, "glacier recovery procedure", vectors.vectors)

    assert [result.record.document_id for result in results] == [
        alpha_document.document_id
    ]


def test_chat_citations_never_cross_the_authorized_workspace(tmp_path):
    settings, store, ingestion, embeddings = _services(tmp_path)
    alpha = _scope("alpha")
    beta = _scope("beta")
    alpha_document = _ingest(
        ingestion,
        alpha,
        "alpha-guide",
        "For glacier incidents, enter alpha code ALPHA-77 in the recovery form.",
    )
    beta_document = _ingest(
        ingestion,
        beta,
        "beta-guide",
        "For glacier incidents, enter beta code BETA-88 in the recovery form.",
    )

    response = SupportAgent(settings, embeddings, store).answer(
        alpha, ChatRequest(question="What glacier code belongs in the recovery form?")
    )

    assert response.citations
    assert {citation.document_id for citation in response.citations} == {
        alpha_document.document_id
    }
    assert beta_document.document_id not in {
        citation.document_id for citation in response.citations
    }
