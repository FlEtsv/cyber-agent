"""
AY-04 + AZ-01: Auto-cableado de actuadores por el agente.

El agente lee el "comportamiento esperado" y genera la integración del actuador.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_WIRE_DB = Path(__file__).parent.parent.parent.parent / "data" / "actuator_wire.json"


def _load() -> dict:
    if _WIRE_DB.exists():
        try:
            return json.loads(_WIRE_DB.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict):
    _WIRE_DB.parent.mkdir(parents=True, exist_ok=True)
    _WIRE_DB.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_expected_behavior(cam_id: str, actuator_name: str, behavior: str):
    """Guardar el comportamiento esperado de un actuador para una cámara."""
    data = _load()
    key = f"{cam_id}::{actuator_name}"
    data[key] = {"cam_id": cam_id, "actuator": actuator_name, "behavior": behavior, "status": "unconfigured"}
    _save(data)


def get_wire_status(cam_id: str, actuator_name: str) -> dict:
    """Obtener el estado de cableado de un actuador."""
    data = _load()
    key = f"{cam_id}::{actuator_name}"
    return data.get(key, {"status": "unknown"})


def wire_actuator_with_agent(cam_id: str, actuator_name: str, behavior: str) -> dict:
    """
    AZ-01: El agente lee el comportamiento esperado y configura el actuador.
    Retorna el resultado del cableado.
    """
    data = _load()
    key = f"{cam_id}::{actuator_name}"

    try:
        from app.security.actuators.registry import _actuators
        if actuator_name not in _actuators:
            return {"ok": False, "error": f"Actuador '{actuator_name}' no registrado"}

        # Simular configuración: el agente podría extender esto con LLM
        data[key] = {
            "cam_id": cam_id,
            "actuator": actuator_name,
            "behavior": behavior,
            "status": "configured",
            "configured_by": "agent",
        }
        _save(data)
        logger.info("wire: %s::%s → configured", cam_id, actuator_name)
        return {"ok": True, "status": "amber", "message": "Cableado — pendiente de test"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mark_status(cam_id: str, actuator_name: str, status: str, evidence: str = ""):
    """Marcar estado del actuador: 'unconfigured'|'amber'|'green'|'red'."""
    data = _load()
    key = f"{cam_id}::{actuator_name}"
    entry = data.get(key, {})
    entry.update({"status": status, "evidence": evidence})
    data[key] = entry
    _save(data)


def list_wired(cam_id: str | None = None) -> list[dict]:
    data = _load()
    result = list(data.values())
    if cam_id:
        result = [r for r in result if r.get("cam_id") == cam_id]
    return result
