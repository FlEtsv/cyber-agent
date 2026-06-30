"""
SEC-011: Almacén de ejemplos de entrenamiento de seguridad (STUB — pendiente).

Responsabilidad: guardar pares (evento, respuesta correcta) para fine-tuning
futuro del módulo de seguridad. Incluye ejemplos de falsos positivos, positivos
reales y decisiones de aprobación/rechazo de herramientas peligrosas.
"""
from __future__ import annotations

__all__ = ["record", "export", "count"]


def record(event: str, context: dict, decision: str, correct: bool) -> None:
    """Registra un ejemplo de entrenamiento (no-op en stub)."""
    pass


def export(path: str | None = None) -> list[dict]:
    """Exporta todos los ejemplos guardados (vacío en stub)."""
    return []


def count() -> int:
    return 0
