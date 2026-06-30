"""
AV-01: Actuador HA — Luz (on/off, brillo, color).

Controla luces de Home Assistant como disuasión:
  - PRESENCE: encender al detectar movimiento
  - LIGHT: parpadeo disuasorio (rápido)
  - AUDIO_WARN: luz parpadeante naranja
"""
from __future__ import annotations

from app.security.actuators.base import DeterrenceActuator, Intent


class HALightActuator(DeterrenceActuator):
    name = "ha_light"

    def __init__(self, entity_id: str, label: str = ""):
        self._entity = entity_id
        self._label = label or entity_id

    def supports(self, intent: Intent) -> bool:
        return intent in (Intent.PRESENCE, Intent.LIGHT, Intent.AUDIO_WARN)

    def is_available(self) -> bool:
        try:
            from app.security.ha_tools import available
            return available()
        except Exception:
            return False

    def fire(self, intent: Intent, payload: dict) -> dict:
        from app.security.ha_tools import run
        if intent == Intent.PRESENCE:
            return run("turn_on", self._entity, {"brightness": 128})
        elif intent == Intent.LIGHT:
            return self._flash()
        elif intent == Intent.AUDIO_WARN:
            return run("turn_on", self._entity, {"color_name": "orange", "brightness": 200})
        return {"ok": False, "error": "intent no soportado"}

    def _flash(self) -> dict:
        """Parpadeo disuasorio: 3 ciclos on/off rápidos."""
        import time, threading
        from app.security.ha_tools import run

        def _do_flash():
            for _ in range(3):
                run("turn_on", self._entity, {"brightness": 255})
                time.sleep(0.5)
                run("turn_off", self._entity)
                time.sleep(0.5)
            run("turn_on", self._entity, {"brightness": 128})

        threading.Thread(target=_do_flash, daemon=True).start()
        return {"ok": True, "mode": "flash"}

    def health(self) -> dict:
        return {"ok": self.is_available(), "entity": self._entity}


def register_from_env() -> None:
    """Registra el actuador de luz desde env (HA_LIGHT_ENTITY)."""
    import os
    entity = os.environ.get("HA_LIGHT_ENTITY", "")
    if entity:
        from app.security.actuators.registry import register
        register(HALightActuator(entity))
