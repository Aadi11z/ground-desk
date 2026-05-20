"""Gemini generation helpers for structured support answers."""

from __future__ import annotations

import json
import os
from typing import Protocol


class LLMProvider(Protocol):
    def generate_json(self, system_prompt: str, user_prompt: str, model: str | None) -> dict:
        ...


def get_generation_provider(*, use_template: bool = False) -> LLMProvider:
    if use_template:
        return TemplateProvider()
    return GeminiProvider()


class TemplateProvider:
    """Deterministic offline generator used only for tests and local evals."""

    def generate_json(self, system_prompt: str, user_prompt: str, model: str | None) -> dict:
        evidence = _extract_evidence(user_prompt)
        if not evidence:
            return {
                "answer": "I do not have enough product documentation to answer this confidently.",
                "confidence": 0.0,
                "needs_escalation": True,
                "suggested_ticket_reply": "Thanks for reaching out. I need to escalate this to our support team because I could not find a grounded answer in the available documentation.",
            }
        best = evidence[0]
        answer = f"Based on the available support documentation, {best['text']}"
        if len(answer) > 850:
            answer = answer[:847].rstrip() + "..."
        return {
            "answer": answer,
            "confidence": best.get("score", 0.5),
            "needs_escalation": best.get("score", 0.0) < 0.35,
            "suggested_ticket_reply": f"Thanks for contacting support. {answer}",
        }


class GeminiProvider:
    def generate_json(self, system_prompt: str, user_prompt: str, model: str | None) -> dict:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini generation.")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model or "gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )
        return _parse_json_response(response.text or "{}")


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
