"""Curated, workspace-loadable documents for trying GroundDesk safely."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.models import DocumentRecord
from app.domain.tenancy import TenantScope

from .service import IngestionService


@dataclass(frozen=True)
class TrialDocument:
    filename: str
    title: str
    description: str
    sample_questions: tuple[str, ...]


TRIAL_DOCUMENTS: tuple[TrialDocument, ...] = (
    TrialDocument(
        filename="authentication.md",
        title="Authentication and SSO",
        description="Password reset delivery, SSO setup checks, and escalation guidance.",
        sample_questions=(
            "How long do password reset emails take?",
            "What should I check when an SSO user cannot sign in?",
        ),
    ),
    TrialDocument(
        filename="billing.md",
        title="Billing and Invoices",
        description="Invoice access, billing permissions, refund limits, and escalation details.",
        sample_questions=(
            "Where can a customer download an invoice?",
            "When can an annual plan be refunded?",
        ),
    ),
    TrialDocument(
        filename="product_usage.md",
        title="Product Usage",
        description="Team invitations, invitation expiry, CSV exports, and delivery timing.",
        sample_questions=(
            "How can a workspace owner resend an expired invitation?",
            "Which roles can export a CSV report?",
        ),
    ),
)


def trial_corpus_catalog(corpus_dir: Path) -> list[dict[str, object]]:
    """Return only available, browser-safe catalog metadata."""
    return [
        {
            "title": document.title,
            "description": document.description,
            "sample_questions": list(document.sample_questions),
        }
        for document in TRIAL_DOCUMENTS
        if (corpus_dir / document.filename).is_file()
    ]


def load_trial_corpus(
    ingestion_service: IngestionService, scope: TenantScope
) -> list[DocumentRecord]:
    """Idempotently load the bundled trial documents into one workspace."""
    missing = [
        document.filename
        for document in TRIAL_DOCUMENTS
        if not (ingestion_service.settings.corpus_dir / document.filename).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Trial corpus files are unavailable: {', '.join(missing)}"
        )

    records = []
    for document in TRIAL_DOCUMENTS:
        path = ingestion_service.settings.corpus_dir / document.filename
        records.append(
            ingestion_service.ingest_path(
                scope,
                path,
                source_id=f"trial-corpus:{document.filename}",
                source="Built-in trial corpus",
                title=document.title,
                original_filename=document.filename,
                metadata={"origin": "trial_corpus"},
            )
        )
    return records
