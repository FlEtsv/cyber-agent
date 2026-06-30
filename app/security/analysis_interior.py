"""
AM-05: Detección de problemas interiores — rotura, desorden, anomalía en escena.

Usa el brain_bridge (Pixtral/local) para analizar imágenes de cámara interior
y detectar:
  - objetos rotos o tirados
  - desorden inusual (comparado con baseline)
  - anomalías de escena (incendio, humo, inundación)
  - gato en situación de riesgo
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_PROBLEM_CATEGORIES = {
    "broken_object": {"severity": 0.7, "action": "notify"},
    "disorder": {"severity": 0.4, "action": "notify"},
    "fire_smoke": {"severity": 1.0, "action": "escalate"},
    "water_leak": {"severity": 0.8, "action": "notify"},
    "cat_danger": {"severity": 0.9, "action": "notify"},
    "unknown_anomaly": {"severity": 0.5, "action": "notify"},
}


@dataclass
class InteriorAnalysis:
    cam_id: str
    problems: list[str] = field(default_factory=list)
    severity: float = 0.0
    description: str = ""
    action: str = "ignore"
    ts: float = field(default_factory=time.time)


def analyze(image_b64: str, cam_id: str = "", context: str = "") -> InteriorAnalysis:
    """
    AM-05: Analiza una imagen de cámara interior en busca de problemas.

    Returns:
        InteriorAnalysis con lista de problemas detectados y severidad máxima.
    """
    prompt = _build_prompt(cam_id, context)
    result_text = _call_vision(image_b64, prompt)
    return _parse(cam_id, result_text)


def _build_prompt(cam_id: str, context: str = "") -> str:
    base = (
        "Analiza esta imagen de una cámara interior de un hogar.\n"
        "Detecta si hay alguno de estos problemas:\n"
        "- Objetos rotos, tirados o en posición anómala\n"
        "- Desorden inusual o brusco (señal de caída, pelea de gatos, accidente)\n"
        "- Humo, fuego, o cualquier señal de incendio\n"
        "- Agua derramada o señales de inundación\n"
        "- Gato en situación de riesgo (atrapado, herido, en lugar peligroso)\n\n"
        "Responde en JSON:\n"
        '{"problems": ["broken_object"|"disorder"|"fire_smoke"|"water_leak"|"cat_danger"|"unknown_anomaly"], '
        '"severity": 0.0-1.0, "description": "descripción clara y concisa", "action": "notify|ignore|escalate"}'
    )
    if context:
        base = f"Contexto adicional: {context}\n\n" + base
    return base


def _call_vision(image_b64: str, prompt: str) -> str:
    try:
        from app.security.mistral_sec import vision
        r = vision(image_b64, prompt)
        if r.get("ok"):
            return r["content"]
    except Exception:
        pass
    try:
        from app.security.vision_local import describe_image
        return describe_image(image_b64)
    except Exception:
        return ""


def _parse(cam_id: str, text: str) -> InteriorAnalysis:
    from app.security.decision import parse_visual
    data = parse_visual(text)
    problems = data.get("detected", [])
    if isinstance(problems, str):
        problems = [problems]
    severity = data.get("threat_score", 0.0)
    desc = data.get("description", "")
    action = data.get("action", "ignore")

    # Detectar categorías de problemas por keywords
    text_lower = text.lower()
    detected = []
    for cat in _PROBLEM_CATEGORIES:
        if cat.replace("_", " ") in text_lower or cat in text_lower:
            detected.append(cat)
            cat_sev = _PROBLEM_CATEGORIES[cat]["severity"]
            if cat_sev > severity:
                severity = cat_sev
                action = _PROBLEM_CATEGORIES[cat]["action"]

    return InteriorAnalysis(
        cam_id=cam_id,
        problems=detected or problems,
        severity=severity,
        description=desc,
        action=action,
    )


def notify_if_problem(analysis: InteriorAnalysis) -> bool:
    """Notifica por Telegram si hay un problema relevante. Retorna True si notificó."""
    if analysis.severity < 0.3 or analysis.action == "ignore":
        return False

    emoji = "🔥" if "fire_smoke" in analysis.problems else (
        "🐱" if "cat_danger" in analysis.problems else "⚠️"
    )
    from app.security.telegram.notify import broadcast
    broadcast(
        title=f"{emoji} Problema interior — {analysis.cam_id}",
        body=analysis.description,
        emoji=emoji,
    )
    return True
