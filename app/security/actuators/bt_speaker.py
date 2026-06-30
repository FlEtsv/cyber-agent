"""
AU-02: Actuador altavoz Bluetooth.

Reproduce audio en un altavoz BT emparejado (Windows/Linux).
Usa el sistema de audio del host (no requiere HA).
Fallback a system_speaker si BT no está disponible.
"""
from __future__ import annotations

import logging
import os

from app.security.actuators.base import DeterrenceActuator, Intent

logger = logging.getLogger(__name__)


class BtSpeakerActuator(DeterrenceActuator):
    name = "bt_speaker"

    def __init__(self, device_name: str = ""):
        self._device = device_name

    def supports(self, intent: Intent) -> bool:
        return intent in (Intent.AUDIO_WARN, Intent.NARRATE, Intent.PRESENCE)

    def is_available(self) -> bool:
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-PnpDevice -Class Bluetooth | Where-Object Status -eq OK | Select-Object -First 1"],
                capture_output=True, text=True, timeout=5,
            )
            return "OK" in result.stdout or result.returncode == 0
        except Exception:
            return False

    def fire(self, intent: Intent, payload: dict) -> dict:
        if intent == Intent.NARRATE:
            text = payload.get("text", "Alerta de seguridad")
            return self._speak(text)
        elif intent in (Intent.AUDIO_WARN, Intent.PRESENCE):
            scenario = payload.get("scenario", "warning")
            return self._play_scenario(scenario)
        return {"ok": False, "error": "intent no soportado"}

    def _speak(self, text: str) -> dict:
        try:
            from app.security.audio.tts import speak
            speak(text, lang="es", block=False)
            return {"ok": True, "mode": "tts_bt"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _play_scenario(self, scenario: str) -> dict:
        try:
            from app.security.audio.library import play_scenario
            play_scenario(scenario)
            return {"ok": True, "scenario": scenario}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {"ok": self.is_available(), "device": self._device or "default"}


# Auto-registro al importar
def _auto_register():
    try:
        from app.security.actuators.registry import register
        register(BtSpeakerActuator())
    except Exception:
        pass


_auto_register()
