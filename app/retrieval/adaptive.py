"""Adaptive retrieval planning and lightweight query expansion."""

from __future__ import annotations

from dataclasses import dataclass
import re


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


class AdaptiveQueryPlanner:
    """Deterministic baseline planner that can later be replaced by an LLM router."""

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
            for phrase in ("screenshot", "image", "diagram", "video", "where is the button")
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

    def expand_queries(self, rewritten_query: str, analysis: QueryAnalysis) -> tuple[str, ...]:
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
        deduped = tuple(dict.fromkeys(candidate.strip() for candidate in candidates if candidate.strip()))
        return deduped[: self.multi_query_limit]

    def hyde_query(self, rewritten_query: str) -> str:
        return (
            "A support article explaining the issue, likely cause, and resolution for: "
            f"{rewritten_query}"
        )
