"""
AT-02..AT-04: Registro de actuadores + asignación por cámara + degradación elegante.

El registro mantiene los actuadores disponibles. Para cada cámara se puede
asignar una lista de actuadores ordenados por preferencia.
La degradación elegante (AT-03) elige el mejor disponible para una intención dada.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from app.security.actuators.base import DeterrenceActuator, Intent

_lock = threading.Lock()
_actuators: dict[str, DeterrenceActuator] = {}

# Asignación por cámara: cam_id → [actuator_name, ...] (orden de preferencia)
_CAM_ASSIGNMENTS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "cam_actuators.json"


def register(actuator: DeterrenceActuator):
    """AT-02: Registrar un actuador disponible."""
    with _lock:
        _actuators[actuator.name] = actuator


def list_actuators() -> list[dict]:
    """AT-04: Estado de todos los actuadores."""
    with _lock:
        return [a.health() for a in _actuators.values()]


def best_for(cam_id: str, intent: Intent) -> DeterrenceActuator | None:
    """
    AT-03: Degradación elegante — elige el mejor actuador disponible.

    Orden: primero los asignados a la cámara, luego cualquier global.
    """
    assigned = _load_assignments().get(cam_id, [])
    candidates: list[DeterrenceActuator] = []

    with _lock:
        # Actuadores asignados primero
        for name in assigned:
            if name in _actuators:
                candidates.append(_actuators[name])
        # Fallback: cualquier actuador global
        for a in _actuators.values():
            if a not in candidates:
                candidates.append(a)

    for a in candidates:
        if a.supports(intent) and a.is_available():
            return a
    return None


def assign_to_camera(cam_id: str, actuator_names: list[str]):
    """AT-02: Asignar actuadores a una cámara (por nombre, en orden de preferencia)."""
    data = _load_assignments()
    data[cam_id] = actuator_names
    _save_assignments(data)


def _load_assignments() -> dict:
    if _CAM_ASSIGNMENTS_PATH.exists():
        try:
            return json.loads(_CAM_ASSIGNMENTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_assignments(data: dict):
    _CAM_ASSIGNMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CAM_ASSIGNMENTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
