"""Gemini generation helpers for structured support answers."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Protocol


class LLMProvider(Protocol):
    def generate_json(
        self, system_prompt: str, user_prompt: str, model: str | None
    ) -> dict: ...


def get_generation_provider(
    *,
    use_template: bool = False,
    max_attempts: int = 4,
    retry_base_seconds: float = 2.0,
    request_delay_seconds: float = 0.0,
    fallback_models: tuple[str, ...] = (),
) -> LLMProvider:
    if use_template:
        return TemplateProvider()
    return GeminiProvider(
        max_attempts=max_attempts,
        retry_base_seconds=retry_base_seconds,
        request_delay_seconds=request_delay_seconds,
        fallback_models=fallback_models,
    )


class TemplateProvider:
    """Deterministic offline generator used only for tests and local evals."""

    def generate_json(
        self, system_prompt: str, user_prompt: str, model: str | None
    ) -> dict:
        evidence = _extract_evidence(user_prompt)
        if not evidence:
            return {
                "answer": "I do not have enough product documentation to answer this confidently.",
                "confidence": 0.0,
                "needs_escalation": True,
                "suggested_ticket_reply": "Thanks for reaching out. I need to escalate this to our support team because I could not find a grounded answer in the available documentation.",
                "_generation_model": "template",
            }
        best = evidence[0]
        answer = f"Based on the available support documentation, {best['text']}"
        if len(answer) > 850:
            answer = answer[:847].rstrip() + "..."
        return {
            "answer": answer,
            "confidence": best.get("score", 0.5),
            # SupportAgent has already admitted evidence through its
            # sufficiency gate; retrieval rank is not an escalation signal.
            "needs_escalation": False,
            "suggested_ticket_reply": f"Thanks for contacting support. {answer}",
            "_generation_model": "template",
        }


class GeminiProvider:
    """Structured Gemini generation with bounded transient-error recovery."""

    def __init__(
        self,
        *,
        max_attempts: int = 4,
        retry_base_seconds: float = 2.0,
        request_delay_seconds: float = 0.0,
        fallback_models: tuple[str, ...] = (),
        api_key: str | None = None,
        client=None,
        sleep=time.sleep,
    ):
        self.max_attempts = max(1, max_attempts)
        self.retry_base_seconds = max(0.0, retry_base_seconds)
        self.request_delay_seconds = max(0.0, request_delay_seconds)
        self.fallback_models = tuple(
            candidate.strip() for candidate in fallback_models if candidate.strip()
        )
        self.api_key = api_key
        self.client = client
        self.sleep = sleep

    def generate_json(
        self, system_prompt: str, user_prompt: str, model: str | None
    ) -> dict:
        from google import genai
        from google.genai import types

        api_key = self.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini generation.")

        client = self.client or genai.Client(api_key=api_key)
        primary_model = model or "gemini-2.5-flash"
        models = tuple(dict.fromkeys((primary_model, *self.fallback_models)))
        for index, candidate_model in enumerate(models):
            try:
                payload = self._generate_with_model(
                    client,
                    types,
                    candidate_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                payload["_generation_model"] = candidate_model
                return payload
            except Exception as exc:
                if index == len(models) - 1 or not _should_fallback_model(exc):
                    raise
        raise RuntimeError("Gemini generation failed without a response.")

    def _generate_with_model(
        self, client, types, model: str, *, system_prompt: str, user_prompt: str
    ) -> dict:
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                    ),
                )
                if self.request_delay_seconds:
                    self.sleep(self.request_delay_seconds)
                return _parse_json_response(response.text or "{}")
            except Exception as exc:
                if not _is_retryable_gemini_error(exc) or attempt >= self.max_attempts:
                    raise
                fallback_delay = self.retry_base_seconds * (2 ** (attempt - 1))
                self.sleep(_retry_delay_seconds(exc, fallback=fallback_delay))
        raise RuntimeError("Gemini generation failed without a response.")


def _extract_evidence(prompt: str) -> list[dict]:
    marker = "Evidence JSON:"
    if marker not in prompt:
        return []
    raw = prompt.split(marker, 1)[1].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        cleaned = cleaned.removesuffix("```").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini did not return valid JSON: {cleaned[:300]}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Gemini returned JSON, but not a JSON object.")
    return payload


def _is_retryable_gemini_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code not in {429, 500, 502, 503, 504}:
        return False
    return "GenerateRequestsPerDayPerProjectPerModel" not in str(exc)


def _should_fallback_model(exc: Exception) -> bool:
    """Try an alternate configured model only for model-specific availability failures."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return code in {404, 429, 500, 502, 503, 504}


def _retry_delay_seconds(exc: Exception, *, fallback: float) -> float:
    """Respect provider retry guidance, otherwise use bounded backoff."""
    message = str(getattr(exc, "message", "") or exc)
    match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", message, re.I)
    if match:
        return max(fallback, float(match.group(1)) + 1.0)
    match = re.search(r"retryDelay['\" ]*:\s*['\"]?([0-9]+)s", message, re.I)
    if match:
        return max(fallback, float(match.group(1)) + 1.0)
    return fallback
