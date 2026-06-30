"""
R-02: Análisis de personas en cámara exterior.

Descripción policial completa:
- Etnia/complexión física
- Vestimenta detallada
- Acción y comportamiento
- Puntos clave (anomalías que destacan)
- Dirección de movimiento

Usa Pixtral (SEC_MISTRAL_SEC_API_KEY) para análisis instantáneo.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def analyze(image_b64: str, cam_id: str = "", context: str = "") -> dict:
    """
    R-02: Analiza una imagen de cámara exterior.

    Returns:
        dict con threat_score, detected, description, action, persons (lista)
    """
    if not os.environ.get("SECURITY_ENABLED", "0") == "1":
        return {"ok": False, "error": "SECURITY_ENABLED=0"}

    try:
        from app.security.prompts import build_exterior_prompt
        prompt = build_exterior_prompt(cam_id, context)
    except Exception:
        prompt = _default_exterior_prompt(cam_id, context)

    try:
        from app.security.mistral_sec import vision
        raw = vision(image_b64=image_b64, prompt=prompt)
        from app.security.decision import parse_visual
        result = parse_visual(raw)
        result["persons"] = _extract_persons(raw)
        return result
    except Exception as e:
        logger.error("analysis_exterior.analyze: %s", e)
        return {
            "threat_score": 0.0,
            "detected": False,
            "description": "Error en el análisis",
            "action": "notify",
            "confidence": 0.0,
            "persons": [],
            "error": str(e),
        }


def _default_exterior_prompt(cam_id: str, context: str) -> str:
    return f"""Eres un sistema de seguridad analizando la cámara exterior {cam_id or 'exterior'}.
Contexto: {context or 'vigilancia de acceso exterior'}

Analiza la imagen y responde en JSON:
{{
  "threat_score": 0.0-1.0,
  "detected": true/false,
  "description": "descripción detallada",
  "action": "ignore|notify|deter|escalate",
  "confidence": 0.0-1.0,
  "persons": [
    {{
      "count": N,
      "description": "descripción policial detallada: complexión, vestimenta, comportamiento",
      "action": "qué está haciendo",
      "direction": "en qué dirección se mueve",
      "suspicious": true/false
    }}
  ]
}}

Para personas, incluye SIEMPRE:
1. Complexión física y etnia aparente
2. Ropa (color, tipo, marcas visibles)
3. Acción exacta (caminando, mirando, manipulando...)
4. Comportamiento sospechoso (si lo hay)
5. Dirección de movimiento
"""


def _extract_persons(raw_response: str) -> list[dict]:
    """Extrae la lista de personas del texto de respuesta."""
    import json
    import re
    try:
        # Buscar JSON en la respuesta
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data.get("persons", [])
    except Exception:
        pass
    return []


def notify_if_threat(analysis: dict, cam_id: str = "") -> bool:
    """
    Envía notificación Telegram si la amenaza es significativa.
    Retorna True si notificó.
    """
    if not os.environ.get("SECURITY_ENABLED", "0") == "1":
        return False

    threat = analysis.get("threat_score", 0.0)
    action = analysis.get("action", "ignore")

    if action == "ignore" or threat < 0.3:
        return False

    try:
        from app.security.telegram.notify import broadcast
        from app.security.telegram.keyboards import security_keyboard
        persons = analysis.get("persons", [])
        person_text = ""
        if persons:
            p = persons[0]
            person_text = f"\n👤 {p.get('description', '')}"
        text = (
            f"🚨 *Amenaza exterior detectada*\n"
            f"📷 Cámara: {cam_id}\n"
            f"🎯 Nivel: {threat:.0%}\n"
            f"📝 {analysis.get('description', '')}"
            f"{person_text}"
        )
        keyboard = security_keyboard(cam_id=cam_id, event_id="exterior")
        from app.security.telegram.notify import broadcast as tg_broadcast
        tg_broadcast(
            title="Amenaza exterior",
            body=text,
            emoji="🚨",
            keyboard=keyboard,
        )
        return True
    except Exception as e:
        logger.error("analysis_exterior.notify_if_threat: %s", e)
        return False
