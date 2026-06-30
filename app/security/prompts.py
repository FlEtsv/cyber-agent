"""
A-06: Prompts de evento/visual para el brain_bridge.

Construye los prompts que se envían a Mistral/local para:
  - Analizar imágenes de cámara (_build_visual_prompt)
  - Decidir sobre un evento de seguridad (_build_event_prompt)
  - Chat con el usuario desde Telegram (_build_chat_prompt)
"""
from __future__ import annotations

import time


def _context_block(cam_id: str | None = None) -> str:
    try:
        from app.security.property_context import get_context_for_model
        return get_context_for_model(cam_id)
    except Exception:
        return "Propiedad privada bajo vigilancia CyberAgent."


def _zones_block(cam_id: str) -> str:
    try:
        from app.security.zones import get_zones
        zones = get_zones(cam_id)
        if not zones:
            return ""
        lines = ["Zonas configuradas:"]
        for z in zones:
            lines.append(f"  - {z['name']} ({z['type']}): zona de interés")
        return "\n".join(lines)
    except Exception:
        return ""


def build_visual_prompt(cam_id: str, extra_context: str = "") -> str:
    """
    A-06: Prompt para análisis visual de cámara.
    Se envía junto con la imagen a Pixtral.
    """
    ctx = _context_block(cam_id)
    zones = _zones_block(cam_id)
    hora = time.strftime("%H:%M")

    parts = [
        f"Contexto: {ctx}",
        f"Cámara: {cam_id}",
        f"Hora: {hora}",
    ]
    if zones:
        parts.append(zones)
    if extra_context:
        parts.append(f"Contexto adicional: {extra_context}")

    parts.append(
        "\nAnaliza esta imagen de seguridad. Responde en JSON con los campos:\n"
        '{"threat_score": 0.0-1.0, "detected": [lista de objetos/personas/mascotas], '
        '"description": "descripción clara", "action": "notify|ignore|deter|escalate", '
        '"confidence": 0.0-1.0, "false_positive_risk": 0.0-1.0}'
    )

    return "\n".join(parts)


def build_event_prompt(event_type: str, description: str, cam_id: str = "") -> str:
    """
    A-06: Prompt para decisión sobre un evento de seguridad.
    Se envía al chat de Mistral o al modelo local.
    """
    ctx = _context_block(cam_id)

    return (
        f"Eres el cerebro de seguridad de CyberAgent.\n"
        f"Contexto de la propiedad: {ctx}\n\n"
        f"Evento recibido:\n"
        f"  Tipo: {event_type}\n"
        f"  Descripción: {description}\n"
        f"  Cámara: {cam_id or 'desconocida'}\n\n"
        f"Decide qué hacer. Responde en JSON:\n"
        '{"action": "notify|ignore|deter|escalate", "confidence": 0.0-1.0, '
        '"reason": "explicación breve", "threat_score": 0.0-1.0}'
    )


def build_chat_prompt(session_id: str = "") -> str:
    """
    A-04: System prompt para el chat del agente desde Telegram.
    """
    ctx = _context_block()
    return (
        f"Eres CyberAgent, el asistente de seguridad personal de Steve.\n"
        f"Contexto: {ctx}\n"
        f"Puedes consultar cámaras, revisar eventos, activar disuasión y "
        f"controlar el sistema domótico.\n"
        f"Responde de forma concisa y útil. Si hay una amenaza activa, prioriza esa información."
    )
