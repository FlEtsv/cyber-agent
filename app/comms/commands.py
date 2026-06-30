"""
U-05: Comandos de gestión del módulo de comunicaciones.

Permite silenciar, cambiar el nivel mínimo y consultar el estado
desde código (supervisor, web, agente).
"""
from __future__ import annotations

from app.comms import router as _r


def mute() -> dict:
    _r.set_muted(True)
    return {"ok": True, "muted": True}


def unmute() -> dict:
    _r.set_muted(False)
    return {"ok": True, "muted": False}


def set_level(level_name: str) -> dict:
    mapping = {
        "debug": _r.DEBUG, "info": _r.INFO, "success": _r.SUCCESS,
        "warning": _r.WARNING, "error": _r.ERROR, "critical": _r.CRITICAL,
    }
    level = mapping.get(level_name.lower())
    if level is None:
        return {"ok": False, "error": f"Nivel desconocido: {level_name}. Opciones: {list(mapping)}"}
    _r.set_min_level(level)
    return {"ok": True, "min_level": level_name}


def status() -> dict:
    return {
        "available": _r.available(),
        "muted": _r._muted,
        "min_level": _r._LEVEL_NAMES.get(_r._min_level, "?"),
    }
