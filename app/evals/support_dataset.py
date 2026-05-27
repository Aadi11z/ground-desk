"""Product-specific evaluation of GroundDesk support behavior.

Unlike BEIR retrieval evaluation, this module evaluates the product contract on
the bundled support corpus: relevant evidence must be retrieved for answerable
questions, unsupported questions must escalate, and follow-up questions can
use bounded conversation context.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Callable

from ..core.models import ChatRequest
from ..generation.agent import SupportAgent, _retrieval_query, _safe_conversation_context


@dataclass(frozen=True)
class SupportEvalCase:
    case_id: str
    category: str
    question: str
    expected_titles: tuple[str, ...]
    expected_answer_terms: tuple[str, ...]
    should_escalate: bool
    conversation_context: tuple[dict[str, str], ...] = ()

    @property
    def is_answerable(self) -> bool:
        return bool(self.expected_titles)

    @property
    def is_follow_up(self) -> bool:
        return bool(self.conversation_context)


@dataclass(frozen=True)
class SupportEvalDataset:
    name: str
    version: str
    description: str
    corpus: str
    review_status: str
    cases: tuple[SupportEvalCase, ...]


def load_support_dataset(path: Path) -> SupportEvalDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = tuple(_parse_case(item) for item in payload.get("cases", []))
    if not cases:
        raise ValueError(f"Support evaluation dataset contains no cases: {path}")
    identifiers = [case.case_id for case in cases]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Support evaluation case IDs must be unique.")
    return SupportEvalDataset(
        name=str(payload["name"]),
        version=str(payload["version"]),
        description=str(payload.get("description", "")),
        corpus=str(payload["corpus"]),
        review_status=str(payload.get("review_status", "unreviewed")),
        cases=cases,
    )


def evaluate_support_dataset(
    dataset: SupportEvalDataset,
    *,
    agent: SupportAgent,
    top_k: int = 3,
    force_template: bool = True,
    compare_followup_without_context: bool = True,
    completed_results: dict[str, dict] | None = None,
    on_case_completed: Callable[[dict], None] | None = None,
) -> dict:
    """Run evidence, answer-proxy and escalation checks through SupportAgent.

    `answer_term_coverage` is a deterministic coverage proxy, not semantic
    answer correctness. For provider-backed generation, returned failures must
    still be manually reviewed before making answer-quality claims.
    """
    results: list[dict] = []
    answerable_results: list[dict] = []
    no_answer_results: list[dict] = []
    follow_up_results: list[dict] = []
    completed_results = completed_results or {}

    for case in dataset.cases:
        result = completed_results.get(case.case_id)
        if result is None:
            response = agent.answer(
                ChatRequest(question=case.question, top_k=top_k),
                force_template=force_template,
                conversation_context=list(case.conversation_context),
            )
            result = _score_case(
                case, response, retrieval_diagnostics=agent.retriever.last_diagnostics
            )
            if case.is_follow_up and compare_followup_without_context:
                baseline = _score_retrieval_only(
                    case,
                    agent=agent,
                    top_k=top_k,
                    conversation_context=[],
                )
                result["without_context"] = {
                    "top_citation_hit": baseline["top_citation_hit"],
                    "evidence_hit": baseline["evidence_hit"],
                }
                result["context_improved_top_citation"] = bool(
                    result["top_citation_hit"] and not baseline["top_citation_hit"]
                )
            if on_case_completed is not None:
                on_case_completed(result)
        results.append(result)
        if case.is_answerable:
            answerable_results.append(result)
        else:
            no_answer_results.append(result)
        if case.is_follow_up:
            follow_up_results.append(result)

    return {
        "dataset": {
            "name": dataset.name,
            "version": dataset.version,
            "corpus": dataset.corpus,
            "review_status": dataset.review_status,
            "cases": len(dataset.cases),
            "answerable_cases": len(answerable_results),
            "no_answer_cases": len(no_answer_results),
            "follow_up_cases": len(follow_up_results),
        },
        "top_k": top_k,
        "generation_mode": "template" if force_template else "provider",
        "metrics": {
            "answerable_evidence_hit_rate": _rate(answerable_results, "evidence_hit"),
            "answerable_top_citation_accuracy": _rate(
                answerable_results, "top_citation_hit"
            ),
            "answerable_citation_precision": _mean(
                [float(item["citation_precision"]) for item in answerable_results]
            ),
            "answer_term_coverage": _rate(answerable_results, "answer_term_hit"),
            "escalation_accuracy": _rate(results, "escalation_hit"),
            "answerable_non_escalation_accuracy": _rate(
                answerable_results, "escalation_hit"
            ),
            "no_answer_escalation_accuracy": _rate(
                no_answer_results, "escalation_hit"
            ),
            "follow_up_evidence_hit_rate": _rate(follow_up_results, "evidence_hit"),
            "follow_up_top_citation_accuracy": _rate(
                follow_up_results, "top_citation_hit"
            ),
            "follow_up_without_context_top_citation_accuracy": _rate_nested(
                follow_up_results, "without_context", "top_citation_hit"
            ),
        },
        "results": results,
    }


def report_as_markdown(report: dict) -> str:
    dataset = report["dataset"]
    metrics = report["metrics"]
    generation_models = sorted(
        {
            str(result["generation_model"])
            for result in report["results"]
            if result.get("generation_model")
        }
    )
    lines = [
        "# GroundDesk Support Evaluation Report",
        "",
        f"- **Dataset:** `{dataset['name']}` v{dataset['version']}",
        f"- **Corpus:** `{dataset['corpus']}`",
        f"- **Cases:** {dataset['cases']} ({dataset['answerable_cases']} answerable, "
        f"{dataset['no_answer_cases']} no-answer/ambiguous, {dataset['follow_up_cases']} follow-up)",
        f"- **Review status:** {dataset['review_status']}",
        f"- **Generation mode:** `{report['generation_mode']}`",
        f"- **Generation models used:** `{', '.join(generation_models) or 'none (gated before generation)'}`",
        f"- **Retrieved citations per answer (top_k):** `{report['top_k']}`",
        "",
        "## Product Behavior Metrics",
        "",
        "| Measure | Score |",
        "| --- | ---: |",
        f"| Relevant evidence retrieved for answerable cases | {_percentage(metrics['answerable_evidence_hit_rate'])} |",
        f"| Correct top citation for answerable cases | {_percentage(metrics['answerable_top_citation_accuracy'])} |",
        f"| Citation precision for answerable cases | {_percentage(metrics['answerable_citation_precision'])} |",
        f"| Expected answer-term coverage | {_percentage(metrics['answer_term_coverage'])} |",
        f"| Escalation decision accuracy, all cases | {_percentage(metrics['escalation_accuracy'])} |",
        f"| Unsupported/ambiguous case escalation accuracy | {_percentage(metrics['no_answer_escalation_accuracy'])} |",
        f"| Follow-up correct top citation with context | {_percentage(metrics['follow_up_top_citation_accuracy'])} |",
        f"| Follow-up correct top citation without context | {_percentage(metrics['follow_up_without_context_top_citation_accuracy'])} |",
        "",
        "## Interpretation Boundary",
        "",
        "- This is a small product-specific evaluation over the bundled demo knowledge base; it is useful for regression and demonstration, not a customer-scale accuracy claim.",
        "- Relevant evidence and escalation labels are explicit. Expected answer-term coverage is a proxy and does not replace human judgement of generated-answer correctness.",
        "- In `template` mode the report tests the retrieval/evidence/escalation pipeline deterministically; run Gemini mode and manually review outputs before discussing live-generation quality.",
        "- Follow-up comparison measures whether stored conversational context improves evidence selection for underspecified later questions.",
        "",
        "## Failed or Weak Cases",
        "",
    ]
    weak = [
        result
        for result in report["results"]
        if not result["escalation_hit"]
        or (result["answerable"] and not result["top_citation_hit"])
        or (result["answerable"] and not result["answer_term_hit"])
    ]
    if not weak:
        lines.append("No labelled checks failed in this run.")
    else:
        lines.extend(
            [
                "| Case | Category | Top citation | Expected | Escalation hit | Answer-term hit |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for result in weak:
            lines.append(
                f"| `{result['case_id']}` | {result['category']} | "
                f"{result['citation_titles'][0] if result['citation_titles'] else 'none'} | "
                f"{', '.join(result['expected_titles']) or 'escalate'} | "
                f"{'yes' if result['escalation_hit'] else 'no'} | "
                f"{'yes' if result['answer_term_hit'] else 'no'} |"
            )
    lines.append("")
    return "\n".join(lines)


def _parse_case(payload: dict) -> SupportEvalCase:
    expected_titles = tuple(str(value) for value in payload.get("expected_titles", []))
    should_escalate = bool(payload.get("should_escalate", False))
    if expected_titles and should_escalate:
        raise ValueError(
            f"Answerable support case cannot require escalation: {payload.get('id')}"
        )
    return SupportEvalCase(
        case_id=str(payload["id"]),
        category=str(payload["category"]),
        question=str(payload["question"]),
        expected_titles=expected_titles,
        expected_answer_terms=tuple(
            str(value) for value in payload.get("expected_answer_terms", [])
        ),
        should_escalate=should_escalate,
        conversation_context=tuple(
            {
                "role": str(message["role"]),
                "content": str(message["content"]),
            }
            for message in payload.get("conversation_context", [])
        ),
    )


def _score_case(case: SupportEvalCase, response, *, retrieval_diagnostics=None) -> dict:
    citation_titles = [citation.title for citation in response.citations]
    expected = {title.lower() for title in case.expected_titles}
    relevant_citations = sum(
        1 for title in citation_titles if title.lower() in expected
    )
    answer_lower = response.answer.lower()
    answer_term_hit = (
        all(term.lower() in answer_lower for term in case.expected_answer_terms)
        if case.expected_answer_terms
        else True
    )
    return {
        "case_id": case.case_id,
        "category": case.category,
        "question": case.question,
        "answerable": case.is_answerable,
        "has_conversation_context": case.is_follow_up,
        "expected_titles": list(case.expected_titles),
        "citation_titles": citation_titles,
        "evidence_hit": bool(expected.intersection(title.lower() for title in citation_titles))
        if expected
        else None,
        "top_citation_hit": bool(citation_titles and citation_titles[0].lower() in expected)
        if expected
        else None,
        "citation_precision": (relevant_citations / len(citation_titles))
        if case.is_answerable and citation_titles
        else (0.0 if case.is_answerable else None),
        "answer_term_hit": answer_term_hit if case.is_answerable else None,
        "expected_escalation": case.should_escalate,
        "needs_escalation": response.needs_escalation,
        "escalation_hit": response.needs_escalation == case.should_escalate,
        "confidence": response.confidence,
        "evidence_status": response.evidence_status,
        "generation_model": response.generation_model,
        "answer": response.answer,
        "trace_id": response.trace_id,
        "retrieval_diagnostics": (
            asdict(retrieval_diagnostics) if retrieval_diagnostics is not None else None
        ),
    }


def _score_retrieval_only(
    case: SupportEvalCase,
    *,
    agent: SupportAgent,
    top_k: int,
    conversation_context: list[dict[str, str]],
) -> dict:
    safe_context = _safe_conversation_context(
        conversation_context,
        max_messages=max(0, agent.settings.conversation_context_turns * 2),
    )
    query = _retrieval_query(case.question, safe_context)
    vectors = agent.embeddings.encode_queries([query]).vectors
    results = agent.retriever.retrieve(query, vectors, top_k=top_k)
    citation_titles = [result.record.title for result in results]
    expected = {title.lower() for title in case.expected_titles}
    return {
        "citation_titles": citation_titles,
        "evidence_hit": bool(expected.intersection(title.lower() for title in citation_titles))
        if expected
        else None,
        "top_citation_hit": bool(citation_titles and citation_titles[0].lower() in expected)
        if expected
        else None,
    }


def _rate(items: list[dict], field: str) -> float | None:
    values = [item[field] for item in items if item.get(field) is not None]
    return _mean([float(bool(value)) for value in values]) if values else None


def _rate_nested(items: list[dict], container: str, field: str) -> float | None:
    values = [
        item[container][field]
        for item in items
        if item.get(container) and item[container].get(field) is not None
    ]
    return _mean([float(bool(value)) for value in values]) if values else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _percentage(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"
