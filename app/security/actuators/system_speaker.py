"""
AU-03: Actuador AltavozSistema — usa el altavoz por defecto del PC.

Implementa DeterrenceActuator. Siempre disponible (si hay audio del sistema).
"""
from __future__ import annotations

from app.security.actuators.base import (
    DeterrenceActuator, ActuatorCapabilities, Intent
)


class SystemSpeakerActuator(DeterrenceActuator):
    name = "system_speaker"
    capabilities = ActuatorCapabilities(
        intents=[Intent.AUDIO_WARN, Intent.NARRATE, Intent.SIREN, Intent.PRESENCE],
        supports_tts=True,
        latency_ms=100,
    )

    def is_available(self) -> bool:
        try:
            import winsound  # noqa — solo verificar que existe
            return True
        except ImportError:
            return False

    def fire(self, intent: Intent, payload: dict | None = None) -> bool:
        payload = payload or {}
        try:
            if intent == Intent.NARRATE:
                text = payload.get("text", "Atención. Intruso detectado.")
                from app.security.audio.tts import speak
                return speak(text)

            elif intent in (Intent.AUDIO_WARN, Intent.SIREN):
                scenario = payload.get("scenario", "warning" if intent == Intent.AUDIO_WARN else "siren")
                from app.security.audio.library import play_scenario
                return play_scenario(scenario)

            elif intent == Intent.PRESENCE:
                import winsound
                winsound.Beep(440, 200)
                return True

            return False
        except Exception:
            return False


# Registrar al importar
from app.security.actuators import registry as _reg
_reg.register(SystemSpeakerActuator())
