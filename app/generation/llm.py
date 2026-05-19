"""LLM provider abstraction for structured support answers."""

from __future__ import annotations

import json
import os
from typing import Protocol


class LLMProvider(Protocol):
    def generate_json(self, system_prompt: str, user_prompt: str, api_key: str | None, model: str | None) -> dict:
        ...


def get_provider(name: str) -> LLMProvider:
    name = (name or "template").lower()
    if name == "openai":
        return OpenAIProvider()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "gemini":
        return GeminiProvider()
    return TemplateProvider()


class TemplateProvider:
    def generate_json(self, system_prompt: str, user_prompt: str, api_key: str | None, model: str | None) -> dict:
        evidence = _extract_evidence(user_prompt)
        question = _extract_between(user_prompt, "Question:", "\n\nEvidence:")
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


class OpenAIProvider:
    def generate_json(self, system_prompt: str, user_prompt: str, api_key: str | None, model: str | None) -> dict:
        from openai import OpenAI

        client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return json.loads(response.choices[0].message.content or "{}")


class AnthropicProvider:
    def generate_json(self, system_prompt: str, user_prompt: str, api_key: str | None, model: str | None) -> dict:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model=model or "claude-sonnet-4-20250514",
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt + "\n\nReturn only valid JSON."}],
        )
        return json.loads(message.content[0].text)


class GeminiProvider:
    def generate_json(self, system_prompt: str, user_prompt: str, api_key: str | None, model: str | None) -> dict:
        import google.generativeai as genai

        genai.configure(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        gemini = genai.GenerativeModel(model or "gemini-1.5-flash", system_instruction=system_prompt)
        response = gemini.generate_content(user_prompt + "\n\nReturn only valid JSON.")
        return json.loads(response.text)


def _extract_between(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    value = text.split(start, 1)[1]
    if end in value:
        value = value.split(end, 1)[0]
    return value.strip()


def _extract_evidence(prompt: str) -> list[dict]:
    marker = "Evidence JSON:"
    if marker not in prompt:
        return []
    raw = prompt.split(marker, 1)[1].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []

