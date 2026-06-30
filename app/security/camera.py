"""
SEC-007: Cámara / visión por computadora (STUB — pendiente de implementar).

Responsabilidad: captura de imagen/vídeo desde cámaras IP/USB, detección de
movimiento, envío a Mistral Pixtral (nube) para análisis visual, disparo de
alertas automáticas a través de notify.py.

Activo solo si CYBERAGENT_SECURITY_ENABLED=1.
"""
from __future__ import annotations

__all__ = ["start", "stop", "status"]


def start() -> None:
    """Inicia la captura de cámaras."""
    raise NotImplementedError("SEC-007 aún no implementado")


def stop() -> None:
    """Detiene la captura."""
    pass


def status() -> dict:
    return {"enabled": False, "reason": "not_implemented"}
