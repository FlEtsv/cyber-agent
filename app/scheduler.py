"""
SCHED-001 — Programador de tareas autónomas de CyberAgent.

Permite que el agente agende acciones fuera de la conversación:
  - trigger "interval": cada N segundos
  - trigger "at":       una vez en una fecha/hora ISO
  - trigger "file":     cuando cambie un archivo/carpeta (mtime)

Acciones soportadas (seguras, sin ejecutar prompts arbitrarios):
  - {"type": "tool",  "name": "...", "args": {...}}  → execute_tool
  - {"type": "shell", "command": "..."}              → shell PowerShell

El motor es un hilo daemon que arranca SOLO cuando hay tareas (opt-in), así no
afecta al inicio de la app. Estado persistido en data/scheduled_tasks.json.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_STORE = os.path.join(_DATA_DIR, "scheduled_tasks.json")
_LOG = os.path.join(_DATA_DIR, "scheduled_runs.jsonl")

_LOCK = threading.RLock()
_THREAD: threading.Thread | None = None
_STOP = threading.Event()
_POLL_SECS = 5
_MAX_RUNS_LOG = 500


# ── Persistencia ─────────────────────────────────────────────────────────────
def _load() -> list[dict]:
    try:
        with open(_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(tasks: list[dict]) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    tmp = _STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _STORE)


def _log_run(entry: dict) -> None:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Ejecución de acciones ────────────────────────────────────────────────────
def _run_action(action: dict) -> dict:
    atype = (action or {}).get("type")
    try:
        if atype == "tool":
            from app.tools import execute_tool
            return execute_tool(action.get("name", ""), action.get("args", {}) or {})
        if atype == "shell":
            from app.tools import execute_tool
            return execute_tool("shell", {"command": action.get("command", "")})
        return {"error": f"tipo de acción no soportado: {atype}"}
    except Exception as exc:
        return {"error": str(exc)}


def _notify(title: str, body: str) -> None:
    try:
        from app.tools import execute_tool
        execute_tool("windows_notify", {"title": title, "message": body[:200]})
    except Exception:
        pass


# ── Cálculo de "vencimiento" ─────────────────────────────────────────────────
def _is_due(task: dict, now: float) -> bool:
    trig = task.get("trigger", {})
    ttype = trig.get("type")
    last = task.get("_last_run", 0)
    if ttype == "interval":
        return (now - last) >= max(5, int(trig.get("seconds", 60)))
    if ttype == "at":
        when = trig.get("iso", "")
        try:
            ts = datetime.fromisoformat(when).timestamp()
        except Exception:
            return False
        return now >= ts and not task.get("_done")
    if ttype == "file":
        path = trig.get("path", "")
        try:
            mt = os.path.getmtime(path)
        except Exception:
            return False
        prev = task.get("_file_mtime")
        task["_file_mtime"] = mt
        return prev is not None and mt > prev
    return False


# ── Bucle del motor ──────────────────────────────────────────────────────────
def _loop() -> None:
    while not _STOP.is_set():
        try:
            with _LOCK:
                tasks = _load()
                changed = False
                now = time.time()
                remaining = []
                for t in tasks:
                    if not t.get("enabled", True):
                        remaining.append(t)
                        continue
                    due = _is_due(t, now)
                    if due:
                        result = _run_action(t.get("action", {}))
                        t["_last_run"] = now
                        t["_runs"] = t.get("_runs", 0) + 1
                        _log_run({"id": t["id"], "name": t.get("name", ""),
                                  "ts": now, "ok": "error" not in result,
                                  "result_preview": json.dumps(result, ensure_ascii=False)[:400]})
                        if t.get("notify", True):
                            _notify(f"Tarea programada: {t.get('name', t['id'])}",
                                    "OK" if "error" not in result else f"Error: {result.get('error')}")
                        changed = True
                        if t.get("trigger", {}).get("type") == "at":
                            t["_done"] = True
                            if not t.get("keep"):
                                continue  # one-shot → se elimina
                    remaining.append(t)
                if changed or len(remaining) != len(tasks):
                    _save(remaining)
        except Exception:
            pass
        _STOP.wait(_POLL_SECS)


def _ensure_running() -> None:
    global _THREAD
    with _LOCK:
        if _THREAD is None or not _THREAD.is_alive():
            _STOP.clear()
            _THREAD = threading.Thread(target=_loop, daemon=True, name="ca-scheduler")
            _THREAD.start()


# ── API pública (usada por las tools) ────────────────────────────────────────
def _is_dangerous_action(action: dict) -> bool:
    """Una acción programada es peligrosa si es shell o una tool peligrosa."""
    atype = action.get("type")
    if atype == "shell":
        return True
    if atype == "tool":
        try:
            from app.tools import is_dangerous
            return is_dangerous(action.get("name", ""))
        except Exception:
            return True
    return False


def add_task(name: str, trigger: dict, action: dict,
             notify: bool = True, keep: bool = False,
             allow_dangerous: bool = False) -> dict:
    valid_trig = {"interval", "at", "file"}
    if trigger.get("type") not in valid_trig:
        return {"ok": False, "error": f"trigger.type debe ser uno de {valid_trig}"}
    if action.get("type") not in {"tool", "shell"}:
        return {"ok": False, "error": "action.type debe ser 'tool' o 'shell'"}
    # Blindaje: una tarea programada que correría sin supervisión NO puede
    # ejecutar shell ni herramientas peligrosas salvo allow_dangerous explícito.
    if _is_dangerous_action(action) and not allow_dangerous:
        return {"ok": False,
                "error": "Esta acción programada es peligrosa (shell o herramienta de riesgo) y se "
                         "ejecutaría sin aprobación. Requiere allow_dangerous=true para confirmarla "
                         "explícitamente, o usa una herramienta no peligrosa.",
                "requires_confirmation": True}
    task = {
        "id": uuid.uuid4().hex[:10],
        "name": name or "tarea",
        "trigger": trigger,
        "action": action,
        "notify": bool(notify),
        "keep": bool(keep),
        "enabled": True,
        "created": time.time(),
        "_runs": 0,
    }
    with _LOCK:
        tasks = _load()
        tasks.append(task)
        _save(tasks)
    _ensure_running()
    return {"ok": True, "id": task["id"], "task": task}


def list_tasks() -> dict:
    with _LOCK:
        tasks = _load()
    return {"ok": True, "count": len(tasks), "tasks": tasks}


def cancel_task(task_id: str) -> dict:
    with _LOCK:
        tasks = _load()
        new = [t for t in tasks if t.get("id") != task_id]
        if len(new) == len(tasks):
            return {"ok": False, "error": f"no existe la tarea {task_id}"}
        _save(new)
    return {"ok": True, "cancelled": task_id, "remaining": len(new)}


def start_if_pending() -> None:
    """Llamar al arrancar la app para reanudar tareas persistidas."""
    if _load():
        _ensure_running()
