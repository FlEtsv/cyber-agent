"""
AH-01: Telemetría de uso de tools por modelo.

Registra qué herramientas usa más cada modelo, para generar ejemplos de
entrenamiento con orquestación correcta de tools (AH-02).

Integra con training_store: cada ejecución de tool exitosa se puede registrar
con kind='tool_usage' y meta={model, tool, success, latency_ms}.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "tool_telemetry.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS tool_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    model       TEXT    NOT NULL,
    tool        TEXT    NOT NULL,
    success     INTEGER NOT NULL DEFAULT 1,
    latency_ms  INTEGER NOT NULL DEFAULT 0,
    approved    INTEGER NOT NULL DEFAULT 1  -- 1=auto, 0=requirió aprobación
);
CREATE INDEX IF NOT EXISTS idx_tu_model ON tool_usage (model);
CREATE INDEX IF NOT EXISTS idx_tu_tool  ON tool_usage (tool);
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


def record(
    model: str,
    tool: str,
    success: bool = True,
    latency_ms: int = 0,
    approved: bool = True,
) -> int:
    """Registra un uso de herramienta."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO tool_usage (ts, model, tool, success, latency_ms, approved) VALUES (?,?,?,?,?,?)",
            (ts, model, tool, int(success), latency_ms, int(approved)),
        )
        return cur.lastrowid or 0


def top_tools(model: str | None = None, limit: int = 20) -> list[dict]:
    """Retorna las herramientas más usadas, opcionalmente por modelo."""
    query = "SELECT tool, model, COUNT(*) as n, AVG(success) as success_rate FROM tool_usage"
    params: list = []
    if model:
        query += " WHERE model=?"
        params.append(model)
    query += " GROUP BY tool ORDER BY n DESC LIMIT ?"
    params.append(limit)
    with _lock, _conn() as c:
        rows = c.execute(query, params).fetchall()
    return [{"tool": r["tool"], "model": r["model"], "count": r["n"],
             "success_rate": round(r["success_rate"] or 0, 3)} for r in rows]


def stats() -> dict:
    with _lock, _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM tool_usage").fetchone()[0]
        models = c.execute("SELECT DISTINCT model FROM tool_usage").fetchall()
    return {
        "total_executions": total,
        "models": [r["model"] for r in models],
    }
