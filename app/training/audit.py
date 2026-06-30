"""
AG-05: Registro de cada entrenamiento para auditoría.

Guarda en SQLite el historial de cada run de entrenamiento:
  - modelo, fecha, n_samples, hparams, métricas, resultado (promoted/discarded)
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "training_audit.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    model_id    TEXT    NOT NULL,
    n_samples   INTEGER NOT NULL DEFAULT 0,
    destination TEXT    NOT NULL DEFAULT 'local',
    hparams     TEXT    NOT NULL DEFAULT '{}',
    metrics     TEXT    NOT NULL DEFAULT '{}',
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending|running|done|failed|promoted|discarded
    notes       TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_run_model ON runs (model_id);
CREATE INDEX IF NOT EXISTS idx_run_status ON runs (status);
"""


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _init():
    with _lock, _conn() as c:
        c.executescript(_DDL)


_init()


def record_run(
    model_id: str,
    n_samples: int,
    destination: str = "local",
    hparams: dict | None = None,
    notes: str = "",
) -> int:
    ts = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO runs (ts, model_id, n_samples, destination, hparams, notes) VALUES (?,?,?,?,?,?)",
            (ts, model_id, n_samples, destination,
             json.dumps(hparams or {}, ensure_ascii=False), notes),
        )
        return cur.lastrowid or 0


def update_run(run_id: int, status: str, metrics: dict | None = None, notes: str = "") -> None:
    updates = {"status": status}
    if metrics is not None:
        updates["metrics"] = json.dumps(metrics, ensure_ascii=False)
    if notes:
        updates["notes"] = notes
    set_clause = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [run_id]
    with _lock, _conn() as c:
        c.execute(f"UPDATE runs SET {set_clause} WHERE id=?", vals)


def get_history(model_id: str, limit: int = 20) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM runs WHERE model_id=? ORDER BY id DESC LIMIT ?",
            (model_id, limit),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["hparams"] = json.loads(d.get("hparams") or "{}")
        d["metrics"] = json.loads(d.get("metrics") or "{}")
        result.append(d)
    return result


def all_history(limit: int = 50) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["hparams"] = json.loads(d.get("hparams") or "{}")
        d["metrics"] = json.loads(d.get("metrics") or "{}")
        result.append(d)
    return result
