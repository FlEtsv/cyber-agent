"""
A-01..A-08: brain_bridge — cerebro del módulo de seguridad.

Rutas de procesamiento:
  A-03: VISIÓN → Mistral Pixtral (imagen de cámara → análisis JSON)
  A-04: CHAT   → modelo local cyberagent-24b con tools
  A-05: usa mistral_sec.py con clave separada y rate-limit propio

El bridge también expone:
  - analyze_image(image_b64, cam_id) → dict de análisis visual
  - decide_event(event_type, description, cam_id) → Decision
  - chat(session_id, message, history) → str

A-02: Sesiones mapeadas por session_id (Telegram user_id, relay session, etc.)
A-08: Tests en tests/test_brain_bridge.py (mock Mistral + local)
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)

_hooks: list[Callable] = []
_sessions: dict[str, list[dict]] = {}
_lock = threading.Lock()

__all__ = [
    "analyze_image", "decide_event", "chat",
    "bridge_call", "register_hook", "status",
]


# ── A-01: Endpoint /api/ext/chat (A-01) — sesiones ────────────────────────────

def _get_session(session_id: str) -> list[dict]:
    with _lock:
        return list(_sessions.get(session_id, []))


def _append_session(session_id: str, role: str, content: str) -> None:
    with _lock:
        hist = _sessions.setdefault(session_id, [])
        hist.append({"role": role, "content": content})
        if len(hist) > 40:
            _sessions[session_id] = hist[-40:]


# ── A-03: VISIÓN — Pixtral ─────────────────────────────────────────────────────

def analyze_image(image_b64: str, cam_id: str = "") -> dict:
    """
    A-03: Analiza una imagen de cámara con Pixtral (Mistral nube).

    Returns:
        {'threat_score': float, 'detected': list, 'description': str,
         'action': str, 'confidence': float, 'false_positive_risk': float}
    """
    if os.environ.get("SECURITY_ENABLED", "0") != "1":
        return {"threat_score": 0.0, "description": "SECURITY_ENABLED=0", "action": "ignore", "confidence": 0.0, "detected": []}

    from app.security.prompts import build_visual_prompt
    from app.security.decision import parse_visual

    prompt = build_visual_prompt(cam_id)

    # Intentar Pixtral
    try:
        from app.security.mistral_sec import vision
        result = vision(image_b64, prompt)
        if result.get("ok"):
            parsed = parse_visual(result["content"])
            _record_visual(cam_id, parsed)
            return parsed
    except Exception as e:
        logger.warning("brain_bridge.analyze_image: Pixtral falló: %s", e)

    # Fallback: visión local
    try:
        from app.security.vision_local import describe_image
        desc = describe_image(image_b64)
        return {"threat_score": 0.3, "description": desc, "action": "notify", "confidence": 0.4, "detected": [], "false_positive_risk": 0.5}
    except Exception:
        return {"threat_score": 0.2, "description": "análisis no disponible", "action": "ignore", "confidence": 0.1, "detected": []}


# ── Decisión de eventos (A-04 / local) ────────────────────────────────────────

def decide_event(
    event_type: str,
    description: str,
    cam_id: str = "",
    image_b64: str | None = None,
) -> "Decision":  # noqa: F821
    """
    A-07: Decide qué hacer con un evento de seguridad.

    Rutas (en orden de preferencia):
    1. Pixtral si hay imagen
    2. Mistral chat (SEC key)
    3. Modelo local
    """
    from app.security.prompts import build_event_prompt
    from app.security.decision import Decision, parse

    if image_b64:
        visual = analyze_image(image_b64, cam_id)
        # Construir Decision desde el análisis visual
        from app.security.decision import _clamp
        return Decision(
            action=visual.get("action", "notify"),
            confidence=_clamp(visual.get("confidence", 0.5)),
            reason=visual.get("description", ""),
            threat_score=_clamp(visual.get("threat_score", 0.3)),
            raw=str(visual),
        )

    prompt = build_event_prompt(event_type, description, cam_id)

    # Mistral chat
    try:
        from app.security.mistral_sec import chat as msec_chat
        result = msec_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        if result.get("ok"):
            return parse(result["content"])
    except Exception as e:
        logger.warning("brain_bridge.decide_event: Mistral falló: %s", e)

    # Modelo local via Ollama
    try:
        return _decide_local(prompt)
    except Exception as e:
        logger.error("brain_bridge.decide_event: local falló: %s", e)

    from app.security.decision import _DEFAULTS
    return parse("")  # default seguro


def _decide_local(prompt: str) -> "Decision":
    from app.security.decision import parse
    import httpx
    r = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": "cyberagent", "prompt": prompt, "stream": False},
        timeout=30,
    )
    text = r.json().get("response", "")
    return parse(text)


# ── A-04: CHAT — agente local desde Telegram ───────────────────────────────────

def chat(session_id: str, message: str, history: list[dict] | None = None) -> str:
    """
    A-04: Chat con el agente desde Telegram → modelo local.

    Args:
        session_id: identificador de sesión (ej. "tg_123456")
        message: mensaje del usuario
        history: historial previo (opcional, usa sesión interna si None)

    Returns:
        Respuesta del agente (str)
    """
    if history is None:
        history = _get_session(session_id)

    from app.security.prompts import build_chat_prompt
    system = build_chat_prompt(session_id)

    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": message}]

    # Intentar modelo local Ollama
    try:
        import httpx
        r = httpx.post(
            "http://localhost:11434/api/chat",
            json={"model": "cyberagent", "messages": messages, "stream": False},
            timeout=45,
        )
        if r.status_code == 200:
            reply = r.json().get("message", {}).get("content", "")
            if reply:
                _append_session(session_id, "user", message)
                _append_session(session_id, "assistant", reply)
                return reply
    except Exception:
        pass

    # Fallback a Mistral medium
    try:
        from app.security.mistral_sec import chat as msec
        result = msec(messages=messages, max_tokens=512)
        if result.get("ok"):
            reply = result["content"]
            _append_session(session_id, "user", message)
            _append_session(session_id, "assistant", reply)
            return reply
    except Exception:
        pass

    return "Lo siento, el agente no está disponible en este momento. Comprueba que el modelo local esté activo."


# ── Hooks (brain_bridge viejo + nuevo) ────────────────────────────────────────

def register_hook(fn: Callable) -> None:
    _hooks.append(fn)


def bridge_call(event: str, payload: dict | None = None) -> None:
    for fn in _hooks:
        try:
            fn(event, payload or {})
        except Exception:
            pass


def status() -> dict:
    return {
        "enabled": os.environ.get("SECURITY_ENABLED", "0") == "1",
        "hooks": len(_hooks),
        "active_sessions": len(_sessions),
        "mistral_sec_available": _mistral_available(),
    }


def _mistral_available() -> bool:
    try:
        from app.security.mistral_sec import available
        return available()
    except Exception:
        return False


def _record_visual(cam_id: str, analysis: dict) -> None:
    try:
        from app.training_store import record
        record(
            kind="vision",
            instruction=f"Análisis visual cámara: {cam_id}",
            response=str(analysis),
            signal=0.0,
            meta={"cam_id": cam_id, "threat_score": analysis.get("threat_score", 0)},
        )
    except Exception:
        pass
