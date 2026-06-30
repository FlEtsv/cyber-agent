"""
AO-06 + AQ-05: Reglas de severidad por fuente + horario "no molestar".

- Mapeo SOURCE → Severity por defecto (editable en runtime)
- Horario no-molestar: solo CRÍTICA suena de noche
"""
from __future__ import annotations

import time
from app.comms.levels import Severity

# Reglas por fuente — editable en runtime
_SOURCE_SEVERITY: dict[str, Severity] = {
    "agent": Severity.MEDIA,
    "security": Severity.ALTA,
    "threat": Severity.CRITICA,
    "cats": Severity.MEDIA,
    "pet": Severity.MEDIA,
    "system": Severity.BAJA,
    "error": Severity.ALTA,
    "training": Severity.BAJA,
    "digest": Severity.PERIODICA,
    "approval": Severity.ALTA,
}

# Horario no-molestar (AQ-05)
_NO_DISTURB_START = 23   # 23:00
_NO_DISTURB_END = 8      # 08:00

_no_disturb_override: bool | None = None  # None = usar horario; True/False = forzar


def get_severity_for_source(source: str, default: Severity = Severity.MEDIA) -> Severity:
    return _SOURCE_SEVERITY.get(source, default)


def set_source_severity(source: str, severity: Severity):
    _SOURCE_SEVERITY[source] = severity


def is_no_disturb_now() -> bool:
    if _no_disturb_override is not None:
        return _no_disturb_override
    hour = int(time.localtime().tm_hour)
    if _NO_DISTURB_START <= _NO_DISTURB_END:
        return _NO_DISTURB_START <= hour < _NO_DISTURB_END
    return hour >= _NO_DISTURB_START or hour < _NO_DISTURB_END


def set_no_disturb(value: bool | None):
    """None = auto por horario; True/False = forzar."""
    global _no_disturb_override
    _no_disturb_override = value


def should_silence(severity: Severity) -> bool:
    """¿Silenciar esta notificación? CRÍTICA nunca se silencia."""
    if severity == Severity.CRITICA:
        return False
    return is_no_disturb_now()
