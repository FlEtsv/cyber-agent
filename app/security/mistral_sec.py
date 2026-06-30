"""
A-05: Cliente Mistral con la 2ª clave (SEC_MISTRAL_SEC_*) — rate-limit independiente.

Usa la clave de seguridad separada de la de CyberAgent principal para no
mezclar quotas. Si no está configurada, cae al cliente principal.
"""
from __future__ import annotations

import logging
import os
import time
import threading

import httpx

logger = logging.getLogger(__name__)

_MISTRAL_API = "https://api.mistral.ai/v1"
_RATE_WINDOW = 60       # segundos
_MAX_CALLS = 10         # llamadas por ventana
_lock = threading.Lock()
_call_times: list[float] = []


def _token() -> str | None:
    try:
        from app.secrets_vault import get_secret
        return (
            get_secret("SEC_MISTRAL_SEC_API_KEY")
            or get_secret("SEC_MISTRAL_API_KEY")
            or os.environ.get("SEC_MISTRAL_SEC_API_KEY")
            or os.environ.get("MISTRAL_API_KEY")
        )
    except Exception:
        return os.environ.get("MISTRAL_API_KEY")


def _check_rate() -> bool:
    """Retorna True si se puede hacer una llamada. False si se excede el límite."""
    now = time.time()
    with _lock:
        # Limpiar timestamps fuera de la ventana
        while _call_times and now - _call_times[0] > _RATE_WINDOW:
            _call_times.pop(0)
        if len(_call_times) >= _MAX_CALLS:
            return False
        _call_times.append(now)
        return True


def chat(
    messages: list[dict],
    model: str = "mistral-medium-latest",
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> dict:
    """
    A-05: Llamada al chat de Mistral con la clave de seguridad.

    Args:
        messages: lista [{role, content}]
        model: ID del modelo Mistral
        max_tokens: tokens máximos de respuesta
        temperature: temperatura

    Returns:
        {'ok': bool, 'content': str, 'model': str}
    """
    token = _token()
    if not token:
        return {"ok": False, "error": "SEC_MISTRAL_API_KEY no configurada"}

    if not _check_rate():
        return {"ok": False, "error": "rate_limit_exceeded — espera un momento"}

    try:
        r = httpx.post(
            f"{_MISTRAL_API}/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=30,
        )
        if r.status_code != 200:
            return {"ok": False, "error": f"Mistral HTTP {r.status_code}: {r.text[:200]}"}
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        return {"ok": True, "content": content, "model": data.get("model", model)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def vision(image_b64: str, prompt: str, model: str = "pixtral-12b-2409") -> dict:
    """
    A-03: Análisis visual con Pixtral.

    Args:
        image_b64: imagen en base64 (JPEG/PNG)
        prompt: pregunta o instrucción sobre la imagen
        model: modelo de visión Mistral (pixtral-12b o pixtral-large)
    """
    token = _token()
    if not token:
        return {"ok": False, "error": "No hay clave Mistral de seguridad configurada"}

    if not _check_rate():
        return {"ok": False, "error": "rate_limit_exceeded"}

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }
    ]

    try:
        r = httpx.post(
            f"{_MISTRAL_API}/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 512},
            timeout=30,
        )
        if r.status_code != 200:
            return {"ok": False, "error": f"Pixtral HTTP {r.status_code}: {r.text[:200]}"}
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        return {"ok": True, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def available() -> bool:
    return bool(_token())
