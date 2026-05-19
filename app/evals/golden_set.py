"""Lightweight golden-set evaluation for GroundDesk."""

from __future__ import annotations

from dataclasses import dataclass

from ..generation.agent import SupportAgent
from ..core.models import ChatRequest


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_terms: tuple[str, ...]
    should_escalate: bool = False


GOLDEN_SET = [
    EvalCase("How long does password reset email delivery usually take?", ("password", "email")),
    EvalCase("Can I export invoices from the billing page?", ("invoice", "billing")),
    EvalCase("What should I do if SSO users cannot sign in?", ("sso", "identity")),
    EvalCase("Do you support refunds for annual plans?", ("refund", "annual")),
    EvalCase("Can GroundDesk configure my unrelated payroll software?", tuple(), should_escalate=True),
]


def run_evals(agent: SupportAgent) -> dict:
    results = []
    hits = 0
    escalations = 0
    for case in GOLDEN_SET:
        response = agent.answer(ChatRequest(question=case.question, provider="template"))
        answer_text = response.answer.lower()
        term_hit = all(term.lower() in answer_text for term in case.expected_terms) if case.expected_terms else True
        escalation_hit = response.needs_escalation == case.should_escalate
        hits += int(term_hit)
        escalations += int(escalation_hit)
        results.append(
            {
                "question": case.question,
                "term_hit": term_hit,
                "escalation_hit": escalation_hit,
                "needs_escalation": response.needs_escalation,
                "citations": len(response.citations),
            }
        )
    total = len(GOLDEN_SET)
    return {
        "num_cases": total,
        "term_hit_rate": hits / total,
        "escalation_accuracy": escalations / total,
        "results": results,
    }

