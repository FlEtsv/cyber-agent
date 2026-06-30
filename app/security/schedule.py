"""
D-09: schedule_store — tareas programadas de seguridad.

Persiste en data/security_schedule.json.
El supervisor las ejecuta en el loop periódico.

Tipos de tarea:
  - snapshot: captura imagen de cam_id
  - retention_cleanup: limpiar videos viejos
  - backup_dbs: backup de bases de datos
  - digest_flush: enviar digest acumulado
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)
_PATH = Path("data/security_schedule.json")


def _load() -> list[dict]:
    if _PATH.exists():
        try:
            return json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(tasks: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def add_task(
    task_type: str,
    interval_secs: int,
    params: dict | None = None,
    label: str = "",
) -> dict:
    """Añade una tarea programada."""
    tasks = _load()
    task = {
        "id": uuid.uuid4().hex[:8],
        "type": task_type,
        "interval_secs": interval_secs,
        "params": params or {},
        "label": label or task_type,
        "last_run": 0.0,
        "enabled": True,
    }
    tasks.append(task)
    _save(tasks)
    return task


def remove_task(task_id: str) -> bool:
    tasks = _load()
    before = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]
    _save(tasks)
    return len(tasks) < before


def get_due_tasks() -> list[dict]:
    """Retorna las tareas que deben ejecutarse ahora."""
    now = time.time()
    return [
        t for t in _load()
        if t.get("enabled") and now - t.get("last_run", 0) >= t.get("interval_secs", 9999)
    ]


def mark_ran(task_id: str) -> None:
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["last_run"] = time.time()
    _save(tasks)


def run_due() -> list[str]:
    """Ejecuta las tareas pendientes. Retorna lista de task_ids ejecutados."""
    ran = []
    for task in get_due_tasks():
        try:
            _execute_task(task)
            mark_ran(task["id"])
            ran.append(task["id"])
        except Exception as e:
            logger.error("schedule: error en tarea %s: %s", task["id"], e)
    return ran


def _execute_task(task: dict) -> None:
    t = task["type"]
    p = task.get("params", {})

    if t == "snapshot":
        from app.security.camera import snapshot_by_name
        snapshot_by_name(p.get("cam_id", ""))

    elif t == "retention_cleanup":
        from app.storage.retention import cleanup
        from app.storage.layout import layout
        cleanup(layout.videos)

    elif t == "backup_dbs":
        from app.storage.backup import backup_all
        from app.storage.layout import layout
        from pathlib import Path
        backup_all(Path("data"), layout.backups)

    elif t == "digest_flush":
        from app.comms.digest import get_digest_text
        from app.security.telegram.notify import broadcast
        text = get_digest_text()
        if text:
            broadcast(title="📋 Resumen periódico", body=text, emoji="📋", silent=True)

    else:
        logger.warning("schedule: tarea desconocida: %s", t)


def default_tasks() -> None:
    """Instala las tareas por defecto si no hay ninguna."""
    if _load():
        return
    add_task("retention_cleanup", interval_secs=86400, label="Limpieza videos 15d")
    add_task("backup_dbs", interval_secs=43200, label="Backup DBs cada 12h")
    add_task("digest_flush", interval_secs=1800, label="Digest cada 30min")


def list_tasks() -> list[dict]:
    return _load()
