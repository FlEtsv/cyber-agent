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


# ── AH-02: Generar ejemplos de entrenamiento desde uso exitoso de tools ───────

def generate_training_examples(
    model: str | None = None,
    min_success_rate: float = 0.8,
    limit: int = 500,
) -> int:
    """
    AH-02: Convierte ejecuciones exitosas de tools en datos de entrenamiento.

    Genera pares instrucción→respuesta para enseñar al modelo qué tool usar
    en cada situación. Solo toma las herramientas con alta tasa de éxito.

    Returns:
        Número de ejemplos generados.
    """
    query = """
        SELECT tool, model, COUNT(*) as n, AVG(success) as sr
        FROM tool_usage
        WHERE success=1
    """
    params: list = []
    if model:
        query += " AND model=?"
        params.append(model)
    query += " GROUP BY tool, model HAVING sr>=? ORDER BY n DESC LIMIT ?"
    params += [min_success_rate, limit]

    with _lock, _conn() as c:
        rows = c.execute(query, params).fetchall()

    if not rows:
        return 0

    count = 0
    try:
        from app.training_store import record as ts_record
        for row in rows:
            instruction = (
                f"El usuario necesita usar la herramienta '{row['tool']}'. "
                f"¿Cuándo es correcto llamar a '{row['tool']}'?"
            )
            response = (
                f"La herramienta '{row['tool']}' se debe usar cuando la tarea "
                f"requiere {row['tool'].replace('_', ' ')}. "
                f"Ha sido ejecutada {row['n']} veces con éxito ({row['sr']*100:.0f}% tasa de acierto)."
            )
            ts_record(
                kind="tool_usage_training",
                instruction=instruction,
                response=response,
                signal=row["sr"],
                meta={"tool": row["tool"], "model": row["model"], "count": row["n"]},
            )
            count += 1
    except Exception:
        pass
    return count


# ── AH-03/04: Métricas de acierto del router de tools ─────────────────────────

def tool_accuracy_report(model: str | None = None) -> dict:
    """
    AH-05: Métricas de tasa de herramienta correcta por modelo.

    Returns:
        dict con accuracy global y desglose por tool.
    """
    query = """
        SELECT model, tool,
               COUNT(*) as total,
               SUM(success) as successes,
               AVG(latency_ms) as avg_latency
        FROM tool_usage
    """
    params: list = []
    if model:
        query += " WHERE model=?"
        params.append(model)
    query += " GROUP BY model, tool ORDER BY model, total DESC"

    with _lock, _conn() as c:
        rows = c.execute(query, params).fetchall()

    result: dict = {}
    for row in rows:
        m = row["model"]
        if m not in result:
            result[m] = {"tools": [], "overall_success_rate": 0.0, "total": 0}
        result[m]["tools"].append({
            "tool": row["tool"],
            "total": row["total"],
            "success_rate": round((row["successes"] or 0) / max(row["total"], 1), 3),
            "avg_latency_ms": round(row["avg_latency"] or 0, 1),
        })
        result[m]["total"] += row["total"]

    for m, data in result.items():
        if data["total"] > 0:
            weighted = sum(
                t["success_rate"] * t["total"] for t in data["tools"]
            )
            data["overall_success_rate"] = round(weighted / data["total"], 3)

    return result


def register_router_feedback(
    tool_selected: str,
    tool_correct: str,
    model: str = "tool-router",
) -> None:
    """
    AH-04: Registra acierto/fallo del router de herramientas como dato de entrenamiento.

    Args:
        tool_selected: herramienta que seleccionó el router
        tool_correct: herramienta que era correcta (puede coincidir o no)
        model: modelo de routing a entrenar
    """
    correct = tool_selected == tool_correct
    signal = 1.0 if correct else -1.0
    try:
        from app.training_store import record
        record(
            kind="approval",
            instruction=f"Seleccionar herramienta correcta para la tarea",
            response=tool_selected,
            signal=signal,
            meta={
                "tool_selected": tool_selected,
                "tool_correct": tool_correct,
                "router_model": model,
            },
        )
    except Exception:
        pass
