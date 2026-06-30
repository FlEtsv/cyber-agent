"""
AO-01: Enum de severidad para el módulo de comunicaciones.

CRÍTICA  → sonido + pin + posible repetición hasta ACK
ALTA     → sonido, sin pin
MEDIA    → notificación normal
BAJA     → silenciosa, va a digest
PERIÓDICA → silenciosa, siempre a digest
"""
from __future__ import annotations
from enum import IntEnum


class Severity(IntEnum):
    CRITICA = 5
    ALTA = 4
    MEDIA = 3
    BAJA = 2
    PERIODICA = 1


# Mapeo nivel numérico (router legacy) → Severity
_LEVEL_MAP: dict[int, Severity] = {
    5: Severity.CRITICA,
    4: Severity.ALTA,
    3: Severity.MEDIA,
    2: Severity.BAJA,
    1: Severity.PERIODICA,
    0: Severity.PERIODICA,
}


def from_int(level: int) -> Severity:
    return _LEVEL_MAP.get(level, Severity.MEDIA)


def from_name(name: str) -> Severity:
    try:
        return Severity[name.upper()]
    except KeyError:
        return Severity.MEDIA


# AO-02: Mapeo severidad → tema Telegram y disable_notification
SEVERITY_TOPIC: dict[Severity, str] = {
    Severity.CRITICA: "Urgente",
    Severity.ALTA: "Seguridad",
    Severity.MEDIA: "Notificaciones",
    Severity.BAJA: "Periódico",
    Severity.PERIODICA: "Periódico",
}

SEVERITY_SILENT: dict[Severity, bool] = {
    Severity.CRITICA: False,
    Severity.ALTA: False,
    Severity.MEDIA: False,
    Severity.BAJA: True,
    Severity.PERIODICA: True,
}

SEVERITY_PIN: dict[Severity, bool] = {
    Severity.CRITICA: True,
    Severity.ALTA: False,
    Severity.MEDIA: False,
    Severity.BAJA: False,
    Severity.PERIODICA: False,
}

# AQ-04: Va a digest en lugar de mensaje individual
GOES_TO_DIGEST: set[Severity] = {Severity.BAJA, Severity.PERIODICA}
