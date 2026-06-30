"""
AZ-02..AZ-04: Auto-test de actuadores.

Dispara el actuador y verifica la respuesta → marca VERDE/ROJO con evidencia.
Test periódico de salud + re-test bajo demanda.
"""
from __future__ import annotations

import logging
import time
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_test_results: dict[str, dict] = {}


def run_selftest(actuator_name: str, cam_id: str = "") -> dict:
    """
    AZ-02: Ejecutar un auto-test del actuador.
    Retorna {"ok": bool, "status": "green"|"red"|"amber", "evidence": str}.
    """
    try:
        from app.security.actuators.registry import _actuators
        from app.security.actuators.base import Intent

        if actuator_name not in _actuators:
            return _record_result(actuator_name, cam_id, False, "Actuador no registrado")

        actuator = _actuators[actuator_name]
        if not actuator.is_available():
            return _record_result(actuator_name, cam_id, False, "No disponible")

        # Intento de fuego con PRESENCE (no destructivo)
        test_intent = Intent.PRESENCE
        if not actuator.supports(test_intent):
            # Probar con cualquier intent soportado
            intents = actuator.capabilities.intents
            test_intent = intents[0] if intents else None

        if test_intent is None:
            return _record_result(actuator_name, cam_id, False, "Sin intents disponibles")

        result = actuator.fire(test_intent, {"test": True, "duration": 1})
        evidence = f"intent={test_intent.value} resultado={result}"
        return _record_result(actuator_name, cam_id, result, evidence)

    except Exception as e:
        return _record_result(actuator_name, cam_id, False, str(e))


def _record_result(name: str, cam_id: str, ok: bool, evidence: str) -> dict:
    status = "green" if ok else "red"
    entry = {
        "actuator": name,
        "cam_id": cam_id,
        "ok": ok,
        "status": status,
        "evidence": evidence,
        "ts": time.time(),
    }
    with _lock:
        _test_results[f"{cam_id}::{name}"] = entry

    # Actualizar wire status
    try:
        from app.security.actuators.wire import mark_status
        mark_status(cam_id, name, status, evidence)
    except Exception:
        pass

    # Avisar si pasa a rojo (AZ-05)
    if not ok:
        try:
            from app.comms.router import send_message
            send_message(
                f"🔴 Actuador {name} falló test",
                f"Cámara: {cam_id}\nEvidencia: {evidence}",
                level=2,
                source="actuator",
            )
        except Exception:
            pass

    logger.info("selftest: %s status=%s evidence=%s", name, status, evidence)
    return entry


def get_last_result(actuator_name: str, cam_id: str = "") -> dict | None:
    with _lock:
        return _test_results.get(f"{cam_id}::{actuator_name}")


def schedule_periodic(interval_seconds: int = 3600):
    """AZ-04: Arrancar test periódico en background."""
    def _loop():
        while True:
            time.sleep(interval_seconds)
            try:
                from app.security.actuators.registry import _actuators
                for name in list(_actuators.keys()):
                    run_selftest(name)
            except Exception as e:
                logger.error("selftest.periodic: %s", e)

    t = threading.Thread(target=_loop, daemon=True, name="actuator-selftest")
    t.start()
