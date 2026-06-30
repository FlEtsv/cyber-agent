"""
D-06: action_executor — ejecuta decisiones del brain_bridge con timeout de confirmación.

Flujo:
  1. brain_bridge llama execute(action, ...).
  2. Si autonomy.should_auto_act(risk) → ejecuta directamente.
  3. Si no → pone en cola pending y envía petición de aprobación a Telegram.
  4. Cuando el usuario aprueba/rechaza (callback) → _resolve() ejecuta o cancela.
  5. Timeout: si nadie responde en APPROVAL_TIMEOUT segundos → cancela.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT = int(os.environ.get("ACTION_APPROVAL_TIMEOUT", "120"))  # segundos


@dataclass
class PendingAction:
    run_id: str
    tool: str
    payload: dict
    risk: str          # low | medium | high
    cam_id: str
    created: float = field(default_factory=time.time)
    resolved: bool = False
    result: dict = field(default_factory=dict)
    _event: threading.Event = field(default_factory=threading.Event, repr=False)


_pending: dict[str, PendingAction] = {}
_lock = threading.Lock()


def execute(
    tool: str,
    payload: dict,
    cam_id: str = "",
    risk: str = "medium",
) -> dict:
    """
    D-06: Ejecuta una acción del agente con aprobación condicional.

    Returns:
        {'ok': bool, 'auto': bool, 'run_id': str, 'result': dict}
    """
    from app.security.autonomy import should_auto_act

    if should_auto_act(risk):
        result = _dispatch(tool, payload)
        _record(tool, payload, risk, auto=True, result=result)
        return {"ok": result.get("ok", False), "auto": True, "run_id": "", "result": result}

    # Requiere aprobación
    run_id = uuid.uuid4().hex[:8]
    action = PendingAction(run_id=run_id, tool=tool, payload=payload, risk=risk, cam_id=cam_id)

    with _lock:
        _pending[run_id] = action

    # Notificar por Telegram
    _request_approval(action)

    # Esperar hasta timeout
    granted = action._event.wait(timeout=APPROVAL_TIMEOUT)

    with _lock:
        _pending.pop(run_id, None)

    if not granted or not action.result.get("approved"):
        _record(tool, payload, risk, auto=False, result={"ok": False, "reason": "timeout_or_rejected"})
        return {"ok": False, "auto": False, "run_id": run_id, "reason": "not_approved"}

    result = _dispatch(tool, payload)
    _record(tool, payload, risk, auto=False, result=result)
    return {"ok": result.get("ok", False), "auto": False, "run_id": run_id, "result": result}


def approve(run_id: str, user_id: int = 0) -> bool:
    """Aprueba una acción pendiente desde el callback de Telegram."""
    with _lock:
        action = _pending.get(run_id)
    if not action or action.resolved:
        return False
    action.resolved = True
    action.result = {"approved": True, "by": user_id}
    action._event.set()
    return True


def reject(run_id: str, user_id: int = 0) -> bool:
    """Rechaza una acción pendiente."""
    with _lock:
        action = _pending.get(run_id)
    if not action or action.resolved:
        return False
    action.resolved = True
    action.result = {"approved": False, "by": user_id}
    action._event.set()
    return True


def pending_list() -> list[dict]:
    with _lock:
        return [
            {
                "run_id": a.run_id,
                "tool": a.tool,
                "preview": str(a.payload)[:80],
                "risk": a.risk,
                "cam_id": a.cam_id,
                "age_s": round(time.time() - a.created, 1),
            }
            for a in _pending.values()
            if not a.resolved
        ]


def _dispatch(tool: str, payload: dict) -> dict:
    """Ejecuta la acción concreta."""
    try:
        # Deterrence tools
        if tool.startswith("deter_"):
            from app.security import deterrence_tools
            fn = getattr(deterrence_tools, tool, None)
            if fn:
                return fn(**payload) or {"ok": True}
        # HA tools
        if tool.startswith("ha_"):
            from app.security.ha_tools import _call_ha
            return _call_ha(tool, payload)
        # Notif
        if tool == "notify":
            from app.security.telegram.notify import broadcast
            broadcast(**payload)
            return {"ok": True}
        return {"ok": False, "error": f"tool desconocida: {tool}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _request_approval(action: PendingAction) -> None:
    try:
        from app.security.telegram.notify import broadcast
        from app.security.telegram.keyboards import agent_keyboard
        preview = str(action.payload)[:100]
        broadcast(
            title=f"⏳ Aprobación requerida: {action.tool}",
            body=f"Riesgo: {action.risk}\nCámara: {action.cam_id}\n{preview}",
            emoji="⏳",
            keyboard=agent_keyboard(tool_name=action.tool, run_id=action.run_id),
        )
    except Exception as e:
        logger.error("actions._request_approval: %s", e)


def _record(tool: str, payload: dict, risk: str, auto: bool, result: dict) -> None:
    try:
        from app.training_store import record
        record(
            kind="action",
            instruction=f"Herramienta: {tool}\nPayload: {payload}\nRiesgo: {risk}",
            response=str(result),
            signal=1.0 if result.get("ok") else -0.5,
            meta={"auto": auto, "tool": tool, "risk": risk},
        )
    except Exception:
        pass
