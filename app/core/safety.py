"""Small safety utilities used by API and logging paths."""

from __future__ import annotations

import re


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?:api[_-]?key|x-llm-api-key)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
]


def redact_secrets(text: str | None) -> str:
    if not text:
        return ""
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def strip_prompt_injection(text: str) -> str:
    """Neutralize common instruction-override phrases inside retrieved content."""
    patterns = [
        r"ignore (?:all )?(?:previous|prior|system) instructions",
        r"you are now",
        r"developer message",
        r"system prompt",
        r"reveal (?:the )?(?:secret|api key|prompt)",
    ]
    sanitized = text
    for pattern in patterns:
        sanitized = re.sub(pattern, "[removed unsafe instruction]", sanitized, flags=re.IGNORECASE)
    return sanitized

