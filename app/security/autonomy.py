"""
D-05: Autonomía — modos manual / operativa / alto-impacto.

manual       → toda acción necesita aprobación humana (Telegram)
operativa    → acciones de bajo riesgo automáticas; alertas/disuasión con aprobación
alto-impacto → todo automático incluyendo disuasión fuerte y escalado

Persiste en data/autonomy.json y publica el cambio por events bus.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_PATH = Path("data/autonomy.json")
_VALID_MODES = {"manual", "operativa", "alto-impacto"}

_state: dict = {
    "mode": "manual",
    "changed_at": 0.0,
    "changed_by": "system",
}


def _load() -> None:
    global _state
    if _STATE_PATH.exists():
        try:
            _state = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass


def _save() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")


_load()


def get_mode() -> str:
    return _state.get("mode", "manual")


def set_mode(mode: str, changed_by: str = "user") -> dict:
    if mode not in _VALID_MODES:
        return {"ok": False, "error": f"Modo inválido. Opciones: {', '.join(_VALID_MODES)}"}

    prev = _state.get("mode")
    _state["mode"] = mode
    _state["changed_at"] = time.time()
    _state["changed_by"] = changed_by
    _save()

    # Publicar evento
    try:
        from app.security.events import emit
        emit("autonomy_mode_changed", {"prev": prev, "mode": mode, "by": changed_by})
    except Exception:
        pass

    logger.info("autonomy: modo cambiado %s → %s por %s", prev, mode, changed_by)
    return {"ok": True, "mode": mode, "prev": prev}


def should_auto_act(action_risk: str = "low") -> bool:
    """
    ¿Debe el sistema actuar sin esperar aprobación humana?

    action_risk: 'low' (notif), 'medium' (disuasión suave), 'high' (disuasión fuerte)
    """
    mode = get_mode()
    if mode == "manual":
        return False
    if mode == "operativa":
        return action_risk == "low"
    if mode == "alto-impacto":
        return True
    return False


def requires_approval(action_risk: str = "medium") -> bool:
    """Inverso de should_auto_act."""
    return not should_auto_act(action_risk)


def status() -> dict:
    return {
        "mode": get_mode(),
        "changed_at": _state.get("changed_at", 0),
        "changed_by": _state.get("changed_by", "system"),
        "auto_low": should_auto_act("low"),
        "auto_medium": should_auto_act("medium"),
        "auto_high": should_auto_act("high"),
    }
