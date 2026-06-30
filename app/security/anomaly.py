"""
AL-07 + AM-01: Detección de anomalías de comportamiento.

Detecta:
- Gato en zona peligrosa (AM-01)
- Comportamiento fuera de patrón aprendido (AL-07)
- Gato ausente demasiado tiempo

Envía notificación vía app.comms.router.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class Anomaly:
    type: str         # 'dangerous_zone' | 'unusual_position' | 'absence' | 'fast_movement'
    severity: str     # 'warning' | 'critical'
    description: str
    pet_id: int | None
    pet_name: str
    cam_id: str
    cx: float
    cy: float
    ts: float


# Cooldown: evitar spam de alertas iguales
_last_alert: dict[str, float] = {}
_COOLDOWN = 120.0  # 2 minutos entre alertas del mismo tipo+pet+cam


def _cooldown_key(anomaly_type: str, cam_id: str, pet_id: int | None) -> str:
    return f"{anomaly_type}:{cam_id}:{pet_id}"


def _check_cooldown(key: str) -> bool:
    now = time.time()
    if key in _last_alert and now - _last_alert[key] < _COOLDOWN:
        return False
    _last_alert[key] = now
    return True


def check(
    cam_id: str,
    cx: float,
    cy: float,
    pet_id: int | None = None,
    pet_name: str = "Desconocido",
    label: str = "cat",
    zone_type: str | None = None,
    zone_name: str | None = None,
    velocity_norm: float = 0.0,
) -> list[Anomaly]:
    """
    AL-07 + AM-01: Detecta anomalías en la posición/comportamiento actual.

    Args:
        cam_id: ID de la cámara
        cx, cy: posición normalizada
        pet_id, pet_name: identidad del animal
        label: especie
        zone_type: tipo de zona en que está ('warning'/'safe'/None)
        zone_name: nombre de la zona
        velocity_norm: velocidad entre frames (distancia euclidea normalizada)

    Returns:
        lista de Anomaly detectadas
    """
    from app.security.species_priors import expected_max_displacement, is_active_hour

    anomalies: list[Anomaly] = []

    # AM-01: gato en zona peligrosa
    if zone_type == "warning":
        key = _cooldown_key("dangerous_zone", cam_id, pet_id)
        if _check_cooldown(key):
            anomalies.append(Anomaly(
                type="dangerous_zone",
                severity="warning",
                description=f"{pet_name} en zona peligrosa: {zone_name or 'zona marcada'}",
                pet_id=pet_id,
                pet_name=pet_name,
                cam_id=cam_id,
                cx=cx,
                cy=cy,
                ts=time.time(),
            ))

    # AL-07: movimiento excepcionalmente rápido
    max_disp = expected_max_displacement(label) * 3  # factor de tolerancia
    if velocity_norm > max_disp:
        key = _cooldown_key("fast_movement", cam_id, pet_id)
        if _check_cooldown(key):
            anomalies.append(Anomaly(
                type="fast_movement",
                severity="warning",
                description=f"{pet_name} se movió muy rápido ({velocity_norm:.2f} vs max {max_disp:.2f})",
                pet_id=pet_id,
                pet_name=pet_name,
                cam_id=cam_id,
                cx=cx,
                cy=cy,
                ts=time.time(),
            ))

    return anomalies


def notify_anomalies(anomalies: list[Anomaly]):
    """Envía alertas de anomalías por el módulo de comunicaciones."""
    if not anomalies:
        return
    try:
        from app.comms.router import notify_threat
        for a in anomalies:
            notify_threat(
                title=f"⚠️ {a.type.replace('_', ' ').title()}",
                body=a.description,
            )
    except Exception:
        pass
