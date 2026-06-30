"""
A-07: Parser de decisión del brain_bridge.

Parsea la respuesta JSON del modelo (Mistral o local) a un Decision estructurado.
Maneja respuestas parciales, JSON malformado y texto mixto.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class Decision:
    action: str        # notify | ignore | deter | escalate
    confidence: float  # 0.0-1.0
    reason: str
    threat_score: float
    raw: str           # texto original del modelo


_VALID_ACTIONS = {"notify", "ignore", "deter", "escalate"}
_DEFAULTS = {
    "action": "notify",
    "confidence": 0.5,
    "reason": "sin información suficiente",
    "threat_score": 0.3,
}


def parse(text: str) -> Decision:
    """
    Parsea la respuesta del modelo a Decision.

    Intenta en orden:
    1. JSON directo
    2. JSON embebido en markdown (```json...```)
    3. Extracción por regex de campos clave
    4. Decisión por defecto (notify con baja confianza)
    """
    raw = text.strip()
    data = _try_json(raw) or _try_json_in_markdown(raw) or _extract_by_regex(raw)

    action = data.get("action", _DEFAULTS["action"]).lower()
    if action not in _VALID_ACTIONS:
        action = _DEFAULTS["action"]

    return Decision(
        action=action,
        confidence=_clamp(data.get("confidence", _DEFAULTS["confidence"])),
        reason=data.get("reason", _DEFAULTS["reason"]),
        threat_score=_clamp(data.get("threat_score", _DEFAULTS["threat_score"])),
        raw=raw,
    )


def parse_visual(text: str) -> dict:
    """
    Parsea respuesta de análisis visual (más campos que Decision).
    Retorna dict con threat_score, detected, description, action, confidence.
    """
    data = _try_json(text) or _try_json_in_markdown(text) or _extract_by_regex(text)
    return {
        "threat_score": _clamp(data.get("threat_score", 0.3)),
        "detected": data.get("detected", []),
        "description": data.get("description", text[:200]),
        "action": data.get("action", "notify"),
        "confidence": _clamp(data.get("confidence", 0.5)),
        "false_positive_risk": _clamp(data.get("false_positive_risk", 0.3)),
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _try_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def _try_json_in_markdown(text: str) -> dict | None:
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if m:
        return _try_json(m.group(1))
    # JSON sin bloque de código pero entre llaves
    m2 = re.search(r"\{[\s\S]*?\}", text)
    if m2:
        return _try_json(m2.group(0))
    return None


def _extract_by_regex(text: str) -> dict:
    """Extrae campos clave por patrones de texto libre."""
    data = {}
    for action in _VALID_ACTIONS:
        if action in text.lower():
            data["action"] = action
            break
    m = re.search(r"confidence[:\s]+([0-9.]+)", text, re.IGNORECASE)
    if m:
        data["confidence"] = float(m.group(1))
    m2 = re.search(r"threat[_\s]score[:\s]+([0-9.]+)", text, re.IGNORECASE)
    if m2:
        data["threat_score"] = float(m2.group(1))
    return data


def _clamp(v) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return 0.5
