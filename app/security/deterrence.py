"""
AW-01..AW-08: Lógica de disuasión de la IA.

La IA elige el nivel según amenaza/zona/hora/contexto.
Escalado automático si la amenaza persiste; de-escalado si desaparece.
Registro en training_store para aprendizaje futuro.

Niveles:
  1 presencia → 2 audio → 3 narración → 4 luz → 5 escalar
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field

from app.security.actuators.base import Intent

_lock = threading.Lock()


@dataclass
class DeterrenceState:
    cam_id: str
    level: int = 0               # 0 = inactivo, 1-5 = niveles
    started_at: float = field(default_factory=time.time)
    last_escalate: float = field(default_factory=time.time)
    active: bool = False
    mode: str = "auto"           # 'auto' | 'manual' | 'off' (AW-07)


_states: dict[str, DeterrenceState] = {}

# Cooldown anti-abuso (AX-04)
_ESCALATE_INTERVAL = 30.0       # segundos entre escalados
_MAX_LEVEL = 5


def get_state(cam_id: str) -> DeterrenceState:
    with _lock:
        if cam_id not in _states:
            _states[cam_id] = DeterrenceState(cam_id=cam_id)
        return _states[cam_id]


def set_mode(cam_id: str, mode: str):
    """AW-07: Cambiar modo ('auto'/'manual'/'off')."""
    state = get_state(cam_id)
    with _lock:
        state.mode = mode


def trigger(
    cam_id: str,
    threat_score: float,
    zone_type: str | None = None,
    hour: int | None = None,
    force_level: int | None = None,
) -> bool:
    """
    AW-02: Decide y ejecuta la disuasión.

    Args:
        cam_id: ID de la cámara
        threat_score: 0.0-1.0 (score de amenaza de la IA)
        zone_type: tipo de zona ('warning'/'safe'/None)
        hour: hora actual (0-23)
        force_level: si no None, fuerza este nivel (AW-07 manual)

    Returns:
        True si se ejecutó alguna disuasión
    """
    state = get_state(cam_id)
    with _lock:
        if state.mode == "off":
            return False

    level = force_level if force_level is not None else _compute_level(threat_score, zone_type, hour)
    if level == 0:
        return False

    return _execute_level(cam_id, level)


def escalate(cam_id: str) -> bool:
    """AW-03: Escalar un nivel si la amenaza persiste."""
    state = get_state(cam_id)
    with _lock:
        now = time.time()
        if now - state.last_escalate < _ESCALATE_INTERVAL:
            return False
        new_level = min(state.level + 1, _MAX_LEVEL)
        state.level = new_level
        state.last_escalate = now
    return _execute_level(cam_id, state.level)


def deescalate(cam_id: str):
    """AW-04: Cancelar/de-escalar cuando la amenaza desaparece."""
    state = get_state(cam_id)
    with _lock:
        state.level = 0
        state.active = False


def _compute_level(threat_score: float, zone_type: str | None, hour: int | None) -> int:
    """AW-02: Nivel basado en score, zona y hora."""
    if threat_score < 0.3:
        return 0
    if zone_type == "safe":
        return 0
    if threat_score < 0.5:
        return 1  # presencia
    if threat_score < 0.7:
        return 2  # audio
    if threat_score < 0.85:
        return 3  # narración
    return 4  # luz


_LEVEL_INTENT = {
    1: Intent.PRESENCE,
    2: Intent.AUDIO_WARN,
    3: Intent.NARRATE,
    4: Intent.LIGHT,
    5: Intent.SIREN,
}


def _execute_level(cam_id: str, level: int) -> bool:
    """Ejecuta el actuador correspondiente al nivel (con límites legales AX-01..04)."""
    intent = _LEVEL_INTENT.get(level)
    if not intent:
        return False

    # AX-01..04: verificar límites legales antes de disparar
    try:
        from app.security.legal_limits import check_and_record
        check_result = check_and_record(cam_id, intent.value, level)
        if not check_result["ok"]:
            import logging
            logging.getLogger(__name__).warning(
                "deterrence: bloqueado por límites legales: %s", check_result["reason"]
            )
            return False
    except Exception:
        pass

    # AX-03: incluir aviso legal en NARRATE
    payload: dict = {}
    if intent == Intent.NARRATE:
        try:
            from app.security.legal_limits import legal_notice_text
            payload["text"] = legal_notice_text()
        except Exception:
            pass

    from app.security.actuators.registry import best_for
    actuator = best_for(cam_id, intent)
    if not actuator:
        return False

    result = actuator.fire(intent, payload)
    _record(cam_id, level, intent.value, result)

    state = get_state(cam_id)
    with _lock:
        state.level = level
        state.active = bool(result)
    return bool(result)


def _record(cam_id: str, level: int, action: str, success: bool):
    """AW-08: Registrar disuasión en training_store."""
    try:
        from app.training_store import record
        record(
            kind="event",
            instruction=f"Disuasión cam={cam_id} nivel={level}",
            response=f"Acción={action} éxito={success}",
            signal=1.0 if success else -0.5,
            meta={"cam_id": cam_id, "level": level, "action": action},
        )
    except Exception:
        pass
