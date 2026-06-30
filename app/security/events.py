"""
SEC-009 / SEC-010: Motor de eventos y autonomía (STUB — pendiente de implementar).

Responsabilidad: escuchar eventos de Home Assistant / sensores / cámaras,
evaluar reglas de autonomía y disparar acciones (notificaciones, herramientas
del agente) sin intervención humana cuando el sistema tiene confianza suficiente.

Activo solo si CYBERAGENT_SECURITY_ENABLED=1.
"""
from __future__ import annotations

__all__ = ["start", "stop", "status", "emit"]


def start() -> None:
    """Arranca el bucle de escucha de eventos."""
    raise NotImplementedError("SEC-009 aún no implementado")


def stop() -> None:
    """Detiene el motor de eventos."""
    pass


def status() -> dict:
    return {"enabled": False, "reason": "not_implemented"}


def emit(event: str, payload: dict | None = None) -> None:
    """Emite un evento interno al bus (no-op en stub)."""
    pass
