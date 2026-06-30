"""
AU-04: Biblioteca de sonidos por escenario.

Mapea escenarios (intrusión, gato en peligro, separar gatos, aviso, alarma)
a archivos de audio. Los archivos deben existir en data/sounds/.
Si no existen, genera un tono simple con winsound (beep).
"""
from __future__ import annotations

from pathlib import Path

_SOUNDS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "sounds"

# Mapeo escenario → nombre de archivo en _SOUNDS_DIR
SCENARIO_SOUNDS: dict[str, str] = {
    "intrusion":      "alarm_intrusion.wav",
    "warning":        "alarm_warning.wav",
    "cats_separate":  "sound_cats_separate.wav",  # frecuencia alta para separar gatos
    "cat_danger":     "alarm_cat_danger.wav",
    "doorbell":       "doorbell.wav",
    "siren":          "siren.wav",
    "voice_warning":  "voice_warning.wav",
    "default":        "alarm_warning.wav",
}

# AX-03: Aviso legal de grabación (audio)
LEGAL_NOTICE_SOUND = "legal_notice.wav"


def get_sound_path(scenario: str) -> Path | None:
    """Devuelve el path al archivo de audio para el escenario dado."""
    filename = SCENARIO_SOUNDS.get(scenario, SCENARIO_SOUNDS["default"])
    path = _SOUNDS_DIR / filename
    if path.exists():
        return path
    return None


def play_scenario(scenario: str) -> bool:
    """Reproduce el sonido del escenario. Si no hay archivo, usa beep."""
    path = get_sound_path(scenario)
    if path:
        from app.security.audio.player import play_async
        play_async(path)
        return True
    return _beep_fallback(scenario)


def play_legal_notice() -> bool:
    """AX-03: Reproducir aviso de grabación."""
    return play_scenario("legal_notice") or _beep_fallback("legal_notice")


def _beep_fallback(scenario: str) -> bool:
    try:
        import winsound
        freq = {"intrusion": 1000, "siren": 1500, "cat_danger": 800}.get(scenario, 600)
        winsound.Beep(freq, 500)
        return True
    except Exception:
        return False


def list_scenarios() -> list[str]:
    return list(SCENARIO_SOUNDS.keys())
