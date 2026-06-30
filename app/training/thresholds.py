"""
AD-04 / X-03: umbrales de entrenamiento por modelo, ajustables por el usuario.

Los valores por defecto viven en las ModelCard (registry). Aquí se guardan los
OVERRIDES que el usuario pone desde el menú de Entrenamiento, persistidos en
data/training_thresholds.json. `effective(model_id, default)` devuelve el override
si existe, o el default de la card.
"""
from __future__ import annotations

import json
import os
import threading

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FILE = os.path.join(_BASE, "data", "training_thresholds.json")
_LOCK = threading.Lock()
_CACHE: dict | None = None


def _load() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    try:
        with open(_FILE, encoding="utf-8") as f:
            _CACHE = json.load(f)
    except Exception:
        _CACHE = {}
    return _CACHE


def _save(d: dict) -> None:
    global _CACHE
    os.makedirs(os.path.dirname(_FILE), exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    _CACHE = d


def effective(model_id: str, default: int) -> int:
    """Umbral efectivo: override del usuario si existe, si no el default de la card."""
    with _LOCK:
        v = _load().get(model_id)
    try:
        return int(v) if v is not None else int(default)
    except Exception:
        return int(default)


def set_threshold(model_id: str, value: int) -> dict:
    if value is None or int(value) < 1:
        return {"ok": False, "error": "umbral inválido (mínimo 1)"}
    with _LOCK:
        d = dict(_load())
        d[model_id] = int(value)
        _save(d)
    return {"ok": True, "model_id": model_id, "threshold": int(value)}


def reset(model_id: str) -> dict:
    with _LOCK:
        d = dict(_load())
        d.pop(model_id, None)
        _save(d)
    return {"ok": True, "model_id": model_id}


def all_overrides() -> dict:
    with _LOCK:
        return dict(_load())
