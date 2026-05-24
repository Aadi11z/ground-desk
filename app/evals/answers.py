"""Answer-quality evaluation helpers."""

from __future__ import annotations

from .golden_set import GOLDEN_SET
from ..core.models import ChatRequest
from ..generation.agent import SupportAgent


def run_answer_quality_evals(agent: SupportAgent) -> dict:
    results = []
    faithful = 0
    citation_precision_hits = 0
    citation_recall_hits = 0
    escalation_hits = 0

    for case in GOLDEN_SET:
        response = agent.answer(
            ChatRequest(question=case.question), force_template=True
        )
        answer_text = response.answer.lower()
        expected_term_hit = (
            all(term.lower() in answer_text for term in case.expected_terms)
            if case.expected_terms
            else response.needs_escalation
        )
        citations_present_when_needed = (
            bool(response.citations) if case.expected_terms else not response.citations
        )
        faithful_hit = expected_term_hit and citations_present_when_needed
        precision_hit = not response.citations or any(
            citation.title.lower() in answer_text
            or citation.snippet.lower()[:20] in answer_text
            for citation in response.citations
        )
        recall_hit = bool(response.citations) if case.expected_terms else True
        escalation_hit = response.needs_escalation == case.should_escalate

        faithful += int(faithful_hit)
        citation_precision_hits += int(precision_hit)
        citation_recall_hits += int(recall_hit)
        escalation_hits += int(escalation_hit)
        results.append(
            {
                "question": case.question,
                "faithful": faithful_hit,
                "citation_precision_hit": precision_hit,
                "citation_recall_hit": recall_hit,
                "escalation_hit": escalation_hit,
            }
        )

    total = len(GOLDEN_SET)
    return {
        "num_cases": total,
        "faithfulness": faithful / total if total else 0.0,
        "citation_precision": citation_precision_hits / total if total else 0.0,
        "citation_recall": citation_recall_hits / total if total else 0.0,
        "escalation_accuracy": escalation_hits / total if total else 0.0,
        "results": results,
    }
