"""
SEC-009 / SEC-010: Motor de eventos y autonomía (STUB — pendiente de implementar).

Responsabilidad: escuchar eventos de Home Assistant / sensores / cámaras,
evaluar reglas de autonomía y disparar acciones (notificaciones, herramientas
del agente) sin intervención humana cuando el sistema tiene confianza suficiente.

Activo solo si CYBERAGENT_SECURITY_ENABLED=1.
"""
from __future__ import annotations

__all__ = ["start", "stop", "status", "emit", "record_decision"]


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


def record_decision(
    event_type: str,
    description: str,
    decision: str,
    outcome: str = "",
    signal: float = 0.0,
) -> int:
    """
    K-02: Captura la decisión tomada para un evento de seguridad en training_store.

    Args:
        event_type: tipo de evento (motion_detected, intrusion_alert, etc.)
        description: descripción del evento recibido
        decision: acción que tomó el sistema (notify/ignore/lock/etc.)
        outcome: resultado posterior si se conoce (confirmed/false_alarm)
        signal: +1 si fue correcta, -1 si fue incorrecta, 0 si desconocido
    """
    full_desc = f"Evento: {event_type}\n{description}"
    full_decision = decision
    if outcome:
        full_decision += f"\nResultado: {outcome}"
    try:
        from app.training_store import record_event
        return record_event(event_type, full_desc, full_decision, signal)
    except Exception:
        return 0
