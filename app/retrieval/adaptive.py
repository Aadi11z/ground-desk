"""Retrieval planning.

The deterministic planner remains an offline baseline. The structured planner
is an opt-in production path: it asks a model for search formulations, validates
the response, always retains the original query, and falls back to a plain
hybrid search on any provider or validation failure.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol


EXACT_TOKEN_PATTERN = re.compile(
    r"(?:\b[A-Z]{2,}[_-][A-Z0-9_-]+\b|\b[A-Z]{2,}\d+[A-Z0-9_-]*\b|\b\d+\.\d+(?:\.\d+)?\b)"
)


@dataclass(frozen=True)
class QueryAnalysis:
    semantic_faq: bool
    exact_token_heavy: bool
    ambiguous: bool
    troubleshooting: bool
    multimodal: bool
    out_of_scope: bool


@dataclass(frozen=True)
class RetrievalPlan:
    mode: str
    rewritten_query: str
    search_queries: tuple[str, ...]
    use_hyde: bool
    analysis: QueryAnalysis
    planner: str = "static"
    planner_reason: str | None = None
    planner_fallback: bool = False


class AdaptiveQueryPlanner:
    """Deterministic rules baseline retained for offline comparison."""

    def __init__(self, *, multi_query_limit: int = 3):
        self.multi_query_limit = multi_query_limit

    def analyze(self, query: str) -> QueryAnalysis:
        lowered = query.lower()
        tokens = re.findall(r"[a-z0-9_:-]+", lowered)
        exact_token_heavy = bool(EXACT_TOKEN_PATTERN.search(query))
        troubleshooting = any(
            phrase in lowered
            for phrase in (
                "not working",
                "doesn't work",
                "cannot",
                "can't",
                "failed",
                "failure",
                "error",
                "issue",
                "troubleshoot",
            )
        )
        multimodal = any(
            phrase in lowered
            for phrase in (
                "screenshot",
                "image",
                "diagram",
                "video",
                "where is the button",
            )
        )
        ambiguous = len(tokens) <= 4 or lowered in {"help", "login broken", "it failed"}
        out_of_scope = any(
            phrase in lowered
            for phrase in ("payroll", "weather", "stock price", "restaurant")
        )
        semantic_faq = any(
            lowered.startswith(prefix)
            for prefix in ("how ", "what ", "where ", "when ", "can ", "do ")
        )
        return QueryAnalysis(
            semantic_faq=semantic_faq,
            exact_token_heavy=exact_token_heavy,
            ambiguous=ambiguous,
            troubleshooting=troubleshooting,
            multimodal=multimodal,
            out_of_scope=out_of_scope,
        )

    def plan(self, query: str) -> RetrievalPlan:
        analysis = self.analyze(query)
        rewritten_query = self.rewrite(query, analysis)

        if analysis.exact_token_heavy:
            mode = "hybrid"
        elif analysis.ambiguous:
            mode = "hybrid"
        elif analysis.semantic_faq:
            mode = "dense"
        else:
            mode = "hybrid"

        search_queries = self.expand_queries(rewritten_query, analysis)
        return RetrievalPlan(
            mode=mode,
            rewritten_query=rewritten_query,
            search_queries=search_queries,
            use_hyde=analysis.ambiguous or analysis.troubleshooting,
            analysis=analysis,
            planner="rules",
            planner_reason="legacy_rule_expansion",
        )

    def rewrite(self, query: str, analysis: QueryAnalysis) -> str:
        lowered = query.lower().strip()
        expansions = {
            "login broken": "login failure SSO sign in password reset authentication",
            "can't log in": "login failure SSO sign in password reset authentication",
            "cannot log in": "login failure SSO sign in password reset authentication",
            "refund": "refund annual plan billing invoice",
            "export": "CSV export reports page",
        }
        rewritten = expansions.get(lowered, query.strip())
        if analysis.troubleshooting and "troubleshooting" not in rewritten.lower():
            rewritten = f"{rewritten} troubleshooting resolution"
        return rewritten

    def expand_queries(
        self, rewritten_query: str, analysis: QueryAnalysis
    ) -> tuple[str, ...]:
        candidates = [rewritten_query]
        lowered = rewritten_query.lower()
        if analysis.troubleshooting:
            candidates.append(f"{rewritten_query} error cause fix")
        if "login" in lowered:
            candidates.append("SSO sign in password reset authentication")
        if "refund" in lowered:
            candidates.append("annual plan refund billing policy")
        if "export" in lowered:
            candidates.append("CSV export reports page")
        deduped = tuple(
            dict.fromkeys(
                candidate.strip() for candidate in candidates if candidate.strip()
            )
        )
        return deduped[: self.multi_query_limit]

    def hyde_query(self, rewritten_query: str) -> str:
        return (
            "A support article explaining the issue, likely cause, and resolution for: "
            f"{rewritten_query}"
        )


class StructuredPlannerProvider(Protocol):
    def generate_json(
        self, system_prompt: str, user_prompt: str, model: str | None
    ) -> dict: ...


PLANNER_SYSTEM_PROMPT = """You plan retrieval for a support knowledge base.
Return valid JSON only with these keys:
- rewritten_query: one concise standalone search query preserving the user's intent
- search_queries: up to three alternative searches, including useful product terms
- use_hyde: boolean; use only when a hypothetical support answer is likely to
  improve semantic retrieval for vague troubleshooting language
- reason: a short routing reason
Do not answer the customer question. Do not classify it as unsupported. The
retrieval system must search before deciding whether evidence exists."""


class StructuredQueryPlanner:
    """Model-backed planner with recall-preserving validation and fallback."""

    def __init__(
        self,
        provider: StructuredPlannerProvider,
        *,
        model: str,
        multi_query_limit: int = 3,
    ):
        self.provider = provider
        self.model = model
        self.multi_query_limit = max(1, multi_query_limit)
        self.analysis_planner = AdaptiveQueryPlanner(
            multi_query_limit=self.multi_query_limit
        )

    def plan(self, query: str) -> RetrievalPlan:
        original = query.strip()
        try:
            payload = self.provider.generate_json(
                PLANNER_SYSTEM_PROMPT,
                f"Customer question:\n{original}",
                model=self.model,
            )
            return self._validated_plan(original, payload)
        except Exception:
            return self.fallback_plan(original, reason="planner_unavailable_or_invalid")

    def fallback_plan(self, query: str, *, reason: str) -> RetrievalPlan:
        return RetrievalPlan(
            mode="hybrid",
            rewritten_query=query,
            search_queries=(query,),
            use_hyde=False,
            analysis=self._analysis_without_rejection(query),
            planner="gemini",
            planner_reason=reason,
            planner_fallback=True,
        )

    def hyde_query(self, rewritten_query: str) -> str:
        return self.analysis_planner.hyde_query(rewritten_query)

    def _validated_plan(self, query: str, payload: dict) -> RetrievalPlan:
        rewritten = str(payload.get("rewritten_query", "")).strip()
        if not rewritten or len(rewritten) > 500:
            raise ValueError("Planner returned an invalid rewritten query.")
        raw_queries = payload.get("search_queries", [])
        if not isinstance(raw_queries, list):
            raise ValueError("Planner search_queries must be a list.")
        candidates = [query, rewritten]
        candidates.extend(
            str(value).strip()
            for value in raw_queries
            if str(value).strip() and len(str(value).strip()) <= 500
        )
        search_queries = tuple(dict.fromkeys(candidates))[: self.multi_query_limit]
        if not search_queries:
            raise ValueError("Planner returned no usable search queries.")
        return RetrievalPlan(
            mode="hybrid",
            rewritten_query=rewritten,
            search_queries=search_queries,
            use_hyde=bool(payload.get("use_hyde", False)),
            analysis=self._analysis_without_rejection(query),
            planner="gemini",
            planner_reason=str(payload.get("reason", "structured_rewrite"))[:120],
        )

    def _analysis_without_rejection(self, query: str) -> QueryAnalysis:
        analysis = self.analysis_planner.analyze(query)
        # The planner can propose searches, but it cannot refuse to search.
        return QueryAnalysis(
            semantic_faq=analysis.semantic_faq,
            exact_token_heavy=analysis.exact_token_heavy,
            ambiguous=analysis.ambiguous,
            troubleshooting=analysis.troubleshooting,
            multimodal=analysis.multimodal,
            out_of_scope=False,
        )
