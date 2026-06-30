"""
B-04: viewer_store — registro dinámico de viewers y admins de Telegram.

SQLite: data/tg_viewers.db
  - user_id (int PK)
  - username (text)
  - role: 'admin' | 'viewer'
  - added_ts (float)
  - active (int 0/1)
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

_DB = Path("data/tg_viewers.db")
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB), check_same_thread=False)
    c.execute(
        """CREATE TABLE IF NOT EXISTS viewers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT DEFAULT 'viewer',
            added_ts REAL,
            active INTEGER DEFAULT 1
        )"""
    )
    c.commit()
    return c


def add_viewer(user_id: int, username: str = "", role: str = "viewer") -> None:
    with _lock:
        c = _conn()
        c.execute(
            "INSERT OR REPLACE INTO viewers (user_id, username, role, added_ts, active) VALUES (?,?,?,?,1)",
            (user_id, username, role, time.time()),
        )
        c.commit()
        c.close()


def remove_viewer(user_id: int) -> None:
    with _lock:
        c = _conn()
        c.execute("UPDATE viewers SET active=0 WHERE user_id=?", (user_id,))
        c.commit()
        c.close()


def get_viewers(role: str | None = None) -> list[dict]:
    with _lock:
        c = _conn()
        if role:
            rows = c.execute(
                "SELECT user_id, username, role FROM viewers WHERE active=1 AND role=?", (role,)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT user_id, username, role FROM viewers WHERE active=1"
            ).fetchall()
        c.close()
    return [{"user_id": r[0], "username": r[1], "role": r[2]} for r in rows]


def is_admin(user_id: int) -> bool:
    with _lock:
        c = _conn()
        row = c.execute(
            "SELECT role FROM viewers WHERE user_id=? AND active=1", (user_id,)
        ).fetchone()
        c.close()
    return bool(row and row[0] == "admin")


def is_authorized(user_id: int) -> bool:
    with _lock:
        c = _conn()
        row = c.execute(
            "SELECT 1 FROM viewers WHERE user_id=? AND active=1", (user_id,)
        ).fetchone()
        c.close()
    return bool(row)


def list_all() -> list[dict]:
    return get_viewers()
