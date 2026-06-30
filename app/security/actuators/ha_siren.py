"""
AV-02: Actuador HA — Sirena / alarma.

Activa una sirena de Home Assistant como deterrencia de alto nivel (nivel 4-5).
  - SIREN: sirena completa
  - AUDIO_WARN: pitido corto (si el dispositivo lo soporta)
"""
from __future__ import annotations

import os

from app.security.actuators.base import DeterrenceActuator, Intent


class HASirenActuator(DeterrenceActuator):
    name = "ha_siren"

    def __init__(self, entity_id: str):
        self._entity = entity_id

    def supports(self, intent: Intent) -> bool:
        return intent in (Intent.SIREN, Intent.AUDIO_WARN)

    def is_available(self) -> bool:
        try:
            from app.security.ha_tools import available
            return available()
        except Exception:
            return False

    def fire(self, intent: Intent, payload: dict) -> dict:
        from app.security.ha_tools import run
        if intent == Intent.SIREN:
            return run("turn_on", self._entity)
        elif intent == Intent.AUDIO_WARN:
            # Tono breve (2 segundos)
            import time, threading
            from app.security.ha_tools import run as ha_run
            def _short():
                ha_run("turn_on", self._entity)
                time.sleep(2)
                ha_run("turn_off", self._entity)
            threading.Thread(target=_short, daemon=True).start()
            return {"ok": True, "mode": "short_tone"}
        return {"ok": False, "error": "intent no soportado"}

    def health(self) -> dict:
        return {"ok": self.is_available(), "entity": self._entity}


def register_from_env() -> None:
    entity = os.environ.get("HA_SIREN_ENTITY", "")
    if entity:
        from app.security.actuators.registry import register
        register(HASirenActuator(entity))
