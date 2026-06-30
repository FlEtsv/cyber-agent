"""
AV-04: Actuador HA — TTS por altavoz de HA.

Reproduce mensajes de audio en altavoces integrados en Home Assistant
(Google Home, Echo, altavoces HA TTS, Sonos…).
  - NARRATE: texto a hablar
  - AUDIO_WARN: aviso pregrabado de HA
  - PRESENCE: mensaje de bienvenida/aviso de presencia
"""
from __future__ import annotations

import os

from app.security.actuators.base import DeterrenceActuator, Intent


_DEFAULT_MESSAGE = "Atención: sistema de seguridad activo"
_WARN_MESSAGE = "Presencia detectada. El sistema ha sido notificado."


class HASpeakActuator(DeterrenceActuator):
    name = "ha_speak"

    def __init__(self, entity_id: str, tts_engine: str = "tts.cloud_say"):
        self._entity = entity_id
        self._tts = tts_engine

    def supports(self, intent: Intent) -> bool:
        return intent in (Intent.NARRATE, Intent.AUDIO_WARN, Intent.PRESENCE)

    def is_available(self) -> bool:
        try:
            from app.security.ha_tools import available
            return available()
        except Exception:
            return False

    def fire(self, intent: Intent, payload: dict) -> dict:
        from app.security.ha_tools import run
        if intent == Intent.NARRATE:
            message = payload.get("text", _WARN_MESSAGE)
        elif intent == Intent.AUDIO_WARN:
            message = _WARN_MESSAGE
        elif intent == Intent.PRESENCE:
            message = _DEFAULT_MESSAGE
        else:
            return {"ok": False, "error": "intent no soportado"}
        return run("speak", self._entity, {"message": message})

    def health(self) -> dict:
        return {"ok": self.is_available(), "entity": self._entity}


def register_from_env() -> None:
    entity = os.environ.get("HA_SPEAK_ENTITY", "")
    if entity:
        from app.security.actuators.registry import register
        tts = os.environ.get("HA_TTS_ENGINE", "tts.cloud_say")
        register(HASpeakActuator(entity, tts))
