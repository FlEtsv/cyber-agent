"""
AV-05: Actuador HA — Puntero láser / juguete interactivo (gatos).

Activa un laser interactivo de HA para distraer/mover gatos de zonas peligrosas.
También útil como disuasión suave exterior (luz visible).
  - PRESENCE: activar brevemente
  - AUDIO_WARN: activar en modo aleatorio (si el dispositivo lo soporta)
"""
from __future__ import annotations

import os
import threading
import time

from app.security.actuators.base import DeterrenceActuator, Intent


class HALaserActuator(DeterrenceActuator):
    name = "ha_laser"

    def __init__(self, entity_id: str, auto_off_secs: int = 30):
        self._entity = entity_id
        self._auto_off = auto_off_secs

    def supports(self, intent: Intent) -> bool:
        return intent in (Intent.PRESENCE, Intent.AUDIO_WARN)

    def is_available(self) -> bool:
        try:
            from app.security.ha_tools import available
            return available()
        except Exception:
            return False

    def fire(self, intent: Intent, payload: dict) -> dict:
        from app.security.ha_tools import run
        result = run("turn_on", self._entity)
        # Auto-apagar después de N segundos
        secs = payload.get("duration", self._auto_off)
        entity = self._entity
        def _off():
            time.sleep(secs)
            run("turn_off", entity)
        threading.Thread(target=_off, daemon=True).start()
        return result

    def health(self) -> dict:
        return {"ok": self.is_available(), "entity": self._entity}


def register_from_env() -> None:
    entity = os.environ.get("HA_LASER_ENTITY", "")
    if entity:
        from app.security.actuators.registry import register
        register(HALaserActuator(entity))
