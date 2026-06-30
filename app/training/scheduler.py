"""
AF-09 + AA-06: Scheduler de entrenamiento.

- Pausa el entrenamiento si arranca un juego (GPU ocupada)
- Solo permite entrenar cuando el usuario está presente/activo
- Coordina con seguridad (degrada a nube antes de entrenar)
"""
from __future__ import annotations

import threading
import time


_lock = threading.Lock()
_game_mode_active = False
_user_present = True         # se asume presente hasta que se detecte lo contrario
_training_paused = False


def set_game_mode(active: bool):
    """AA-06: Pausar entrenamiento si arranca un juego."""
    global _game_mode_active, _training_paused
    with _lock:
        _game_mode_active = active
        if active:
            _training_paused = True
        else:
            _training_paused = False


def set_user_present(present: bool):
    """X-05: Marcar si el usuario está presente (detectado por actividad de teclado/ratón)."""
    global _user_present
    with _lock:
        _user_present = present


def can_train() -> tuple[bool, str]:
    """
    X-05: ¿Se puede iniciar entrenamiento ahora?
    Retorna (bool, motivo_si_no).
    """
    with _lock:
        if _game_mode_active:
            return False, "modo_juego activo (GPU reservada)"
        if _training_paused:
            return False, "entrenamiento en pausa"
        if not _user_present:
            return False, "usuario no detectado (solo se entrena con el usuario presente)"
    return True, ""


def status() -> dict:
    with _lock:
        return {
            "game_mode": _game_mode_active,
            "user_present": _user_present,
            "training_paused": _training_paused,
            "can_train": not (_game_mode_active or _training_paused or not _user_present),
        }
