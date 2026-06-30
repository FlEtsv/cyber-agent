"""
AU-06: TTS EN VIVO — la IA narra lo que ve en tiempo real.

Recibe la descripción del evento (de brain_bridge o VLM) y la anuncia
por el altavoz configurado con cadencia inteligente (no spamear).
"""
from __future__ import annotations

import threading
import time

_last_narration: float = 0.0
_MIN_INTERVAL = 15.0  # segundos mínimos entre narraciones
_lock = threading.Lock()


def narrate(description: str, force: bool = False) -> bool:
    """
    AU-06: Narra una descripción en voz alta.

    Args:
        description: texto a narrar
        force: ignorar el cooldown anti-spam

    Returns:
        True si se inició la narración, False si se silencia por cooldown
    """
    global _last_narration
    with _lock:
        now = time.time()
        if not force and (now - _last_narration) < _MIN_INTERVAL:
            return False
        _last_narration = now

    # Recortar si es demasiado largo (narración de máx ~15 segundos)
    text = description[:200] if len(description) > 200 else description

    from app.security.audio.tts import speak
    speak(text, block=False)
    return True


def set_min_interval(secs: float):
    global _MIN_INTERVAL
    _MIN_INTERVAL = secs
