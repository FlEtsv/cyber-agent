from __future__ import annotations

import os
import re
from typing import Any

import httpx


DEFAULT_BASE_URL = "https://api.mistral.ai/v1"
DEFAULT_MODEL = "mistral-large-latest"
MAX_FIELD_CHARS = 12000


_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\";,]+)"), r"\1=<redacted>"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+"), "Bearer <redacted>"),
    (re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"), "<jwt-redacted>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL), "<private-key-redacted>"),
    (re.compile(r"(?i)([?&](?:key|token|secret|password|api_key)=)[^&#\s]+"), r"\1<redacted>"),
]


def _api_key() -> str:
    return (
        os.getenv("MISTRAL_API_KEY")
        or os.getenv("MISTRAL_STUDIO_API_KEY")
        or ""
    ).strip()


def redact_for_cloud(text: str | None) -> str:
    """Remove common credentials before sending context to an external model."""
    if not text:
        return ""
    redacted = str(text)
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    if len(redacted) > MAX_FIELD_CHARS:
        redacted = redacted[:MAX_FIELD_CHARS] + "\n...[truncated for cloud consult]..."
    return redacted


def mistral_available() -> bool:
    return bool(_api_key())


def consult_mistral(
    task: str,
    context: str = "",
    mode: str = "audit",
    allow_sensitive: bool = False,
    max_tokens: int = 900,
) -> dict[str, Any]:
    """
    Ask Mistral Studio for an external review.

    API keys are read from environment variables only. Context is redacted by
    default and request headers are never returned.
    """
    key = _api_key()
    if not key:
        return {
            "ok": False,
            "error": "MISTRAL_API_KEY or MISTRAL_STUDIO_API_KEY is not configured",
            "redacted": not allow_sensitive,
        }

    mode = (mode or "audit").strip().lower()
    max_tokens = max(128, min(int(max_tokens or 900), 4096))
    send_task = task if allow_sensitive else redact_for_cloud(task)
    send_context = context if allow_sensitive else redact_for_cloud(context)

    base_url = os.getenv("MISTRAL_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("CYBERAGENT_MISTRAL_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an external security and engineering reviewer for "
                    "authorized audits. Do not execute actions. Provide concise, "
                    "practical findings, checks, risks, and next steps. If the "
                    "request may expose secrets or private data, call that out."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Mode: {mode}\n\n"
                    f"Task:\n{send_task}\n\n"
                    f"Context:\n{send_context}\n\n"
                    "Return: 1) verdict, 2) blind spots, 3) concrete checks, "
                    "4) recommended next action."
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        if response.status_code >= 400:
            return {
                "ok": False,
                "error": f"Mistral HTTP {response.status_code}: {response.text[:500]}",
                "model": model,
                "mode": mode,
                "redacted": not allow_sensitive,
            }
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "ok": True,
            "model": model,
            "mode": mode,
            "redacted": not allow_sensitive,
            "response": content,
            "usage": data.get("usage", {}),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "model": model,
            "mode": mode,
            "redacted": not allow_sensitive,
        }
