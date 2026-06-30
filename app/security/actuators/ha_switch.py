"""
AV-03: Actuador HA — Enchufe/switch inteligente.

Corta el suministro a un dispositivo (TV, calefactor…) como herramienta
de disuasión o de protección de mascotas.
  - DISCONNECT: apagar el enchufe
  - PRESENCE: encender brevemente (simular presencia)
"""
from __future__ import annotations

import os

from app.security.actuators.base import DeterrenceActuator, Intent


class HASwitchActuator(DeterrenceActuator):
    name = "ha_switch"

    def __init__(self, entity_id: str, label: str = ""):
        self._entity = entity_id
        self._label = label or entity_id

    def supports(self, intent: Intent) -> bool:
        return intent in (Intent.DISCONNECT, Intent.PRESENCE)

    def is_available(self) -> bool:
        try:
            from app.security.ha_tools import available
            return available()
        except Exception:
            return False

    def fire(self, intent: Intent, payload: dict) -> dict:
        from app.security.ha_tools import run
        if intent == Intent.DISCONNECT:
            return run("turn_off", self._entity)
        elif intent == Intent.PRESENCE:
            return run("turn_on", self._entity)
        return {"ok": False, "error": "intent no soportado"}

    def health(self) -> dict:
        return {"ok": self.is_available(), "entity": self._entity}


def register_from_env() -> None:
    entity = os.environ.get("HA_SWITCH_ENTITY", "")
    if entity:
        from app.security.actuators.registry import register
        register(HASwitchActuator(entity))
