"""
AS-03: Registro/auditoría de notificaciones enviadas y acciones ejecutadas.

Guarda en data/comms_audit.db:
- Cada mensaje enviado (canal, severidad, título, ts)
- Cada acción ejecutada desde Telegram (callback, resultado)
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "comms_audit.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS notifications (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    channel   TEXT,
    severity  TEXT,
    title     TEXT,
    body      TEXT,
    source    TEXT,
    ts        REAL,
    ok        INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS actions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER,
    action     TEXT,
    payload    TEXT,
    result     TEXT,
    ts         REAL
);
CREATE INDEX IF NOT EXISTS idx_notif_ts ON notifications (ts DESC);
CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions (ts DESC);
"""


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.executescript(_DDL)
    return c


def log_notification(
    channel: str,
    severity: str,
    title: str,
    body: str = "",
    source: str = "",
    ok: bool = True,
):
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO notifications (channel, severity, title, body, source, ts, ok) VALUES (?,?,?,?,?,?,?)",
            (channel, severity, title, body[:500], source, time.time(), int(ok)),
        )


def log_action(chat_id: int, action: str, payload: str = "", result: str = ""):
    import json
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO actions (chat_id, action, payload, result, ts) VALUES (?,?,?,?,?)",
            (chat_id, action, payload[:300], result[:300], time.time()),
        )


def recent_notifications(n: int = 50) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM notifications ORDER BY ts DESC LIMIT ?", (n,)
        ).fetchall()
    return [dict(r) for r in rows]


def recent_actions(n: int = 50) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM actions ORDER BY ts DESC LIMIT ?", (n,)
        ).fetchall()
    return [dict(r) for r in rows]


def stats() -> dict:
    with _lock, _conn() as c:
        total_notif = c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        total_actions = c.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
    return {"total_notifications": total_notif, "total_actions": total_actions}
