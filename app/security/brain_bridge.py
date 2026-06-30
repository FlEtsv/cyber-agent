"""
SEC-008: Puente cerebro ↔ módulo de seguridad (STUB — pendiente de implementar).

Responsabilidad: integrar el agente principal (app.brain / AgentRunner) con el
subsistema de seguridad. Permite que el agente tome decisiones autónomas basadas
en eventos de seguridad, y que el módulo de seguridad invoque herramientas del
agente (p.ej. enviar un mensaje, activar un dispositivo).

Activo solo si CYBERAGENT_SECURITY_ENABLED=1.
"""
from __future__ import annotations

__all__ = ["bridge_call", "register_hook", "status"]

_hooks: list = []


def register_hook(fn) -> None:
    """Registra una función a llamar cuando el módulo de seguridad emite un evento."""
    _hooks.append(fn)


def bridge_call(event: str, payload: dict | None = None) -> None:
    """Propaga un evento de seguridad al agente. No-op si no hay hooks."""
    for fn in _hooks:
        try:
            fn(event, payload or {})
        except Exception:
            pass


def status() -> dict:
    return {"enabled": False, "hooks": len(_hooks), "reason": "not_implemented"}
