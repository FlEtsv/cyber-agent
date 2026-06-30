"""
BA-01..BA-05: Descubrimiento y emparejamiento de dispositivos HA.

Descubre entidades HA disponibles (luces, enchufes, switches) y permite
vincularlas como actuadores desde el menú.
"""
from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

_SUPPORTED_DOMAINS = ("light", "switch", "media_player", "input_boolean", "siren")


def discover_entities(
    domain: str | None = None,
) -> list[dict]:
    """
    BA-01: Descubrir entidades HA disponibles.
    Si domain=None, devuelve las de todos los dominios soportados.
    """
    from app.security.ha_tools import ha_api
    try:
        states = ha_api("GET", "/api/states") or []
    except Exception as e:
        logger.warning("ha_discovery.discover: %s", e)
        return []

    domains = [domain] if domain else list(_SUPPORTED_DOMAINS)
    result = []
    for state in states:
        entity_id = state.get("entity_id", "")
        if not any(entity_id.startswith(d + ".") for d in domains):
            continue
        result.append({
            "entity_id": entity_id,
            "name": state.get("attributes", {}).get("friendly_name", entity_id),
            "state": state.get("state", "unknown"),
            "domain": entity_id.split(".")[0],
        })
    return result


def add_device_as_actuator(entity_id: str, label: str = "") -> dict:
    """
    BA-02: Vincular una entidad HA como actuador y registrarla.
    """
    domain = entity_id.split(".")[0]
    if domain not in _SUPPORTED_DOMAINS:
        return {"ok": False, "error": f"Dominio '{domain}' no soportado"}

    actuator_name = label or entity_id.replace(".", "_")

    try:
        from app.security.actuators import registry
        from app.security.actuators.base import DeterrenceActuator, ActuatorCapabilities, Intent

        class _DynActuator(DeterrenceActuator):
            name = actuator_name
            capabilities = ActuatorCapabilities(
                intents=[Intent.PRESENCE, Intent.LIGHT, Intent.AUDIO_WARN],
                supports_tts=False,
            )

            def is_available(self):
                return True

            def fire(self, intent, payload=None):
                try:
                    from app.security.ha_tools import ha_api
                    if intent in (Intent.PRESENCE, Intent.LIGHT):
                        ha_api("POST", f"/api/services/{domain}/turn_on",
                               {"entity_id": entity_id})
                    elif intent == Intent.DISCONNECT:
                        ha_api("POST", f"/api/services/{domain}/turn_off",
                               {"entity_id": entity_id})
                    return True
                except Exception:
                    return False

        registry.register(_DynActuator())
        return {"ok": True, "actuator": actuator_name, "entity_id": entity_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_entity(entity_id: str, action: Literal["on", "off", "toggle"] = "toggle") -> bool:
    """BA-04: Probar un dispositivo (on/off/toggle)."""
    domain = entity_id.split(".")[0]
    try:
        from app.security.ha_tools import ha_api
        service = {"on": "turn_on", "off": "turn_off", "toggle": "toggle"}[action]
        ha_api("POST", f"/api/services/{domain}/{service}", {"entity_id": entity_id})
        return True
    except Exception as e:
        logger.warning("ha_discovery.test_entity: %s", e)
        return False


# BA-05: Tipos de actuadores soportados
SUPPORTED_TYPES = [
    {"domain": "light", "label": "Luz inteligente", "description": "Encender/apagar luz"},
    {"domain": "switch", "label": "Enchufe inteligente", "description": "Enchufe con conmutación"},
    {"domain": "siren", "label": "Sirena HA", "description": "Sirena de alarma"},
    {"domain": "media_player", "label": "Altavoz HA", "description": "Reproducir audio/TTS"},
    {"domain": "input_boolean", "label": "Helper booleano", "description": "Activar automatización HA"},
]
