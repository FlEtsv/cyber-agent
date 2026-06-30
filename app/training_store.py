"""
K-01 + K-05: training_store — grifo de datos para QLoRA.

Captura decisiones del agente en formato (instrucción / respuesta / señal)
para entrenamiento futuro en RunPod. SQLite local en data/training.db.
La escritura es append-only; el export genera un JSONL de conversación compatible
con el formato de fine-tuning de Mistral/LLaMA (system + user + assistant).

No importa nada de SECURITY_ENABLED; el store siempre está activo para
capturar cualquier interacción del agente.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "training.db"
_lock = threading.Lock()

# ── Schema ────────────────────────────────────────────────────────────────────

_DDL_TABLE = """
CREATE TABLE IF NOT EXISTS samples (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    kind        TEXT    NOT NULL,   -- 'interaction'|'approval'|'feedback'|'event'|'security'|'reasoning'|'correction'
    instruction TEXT    NOT NULL,   -- system + user context
    response    TEXT    NOT NULL,   -- assistant output / decision
    signal      REAL    DEFAULT 0,  -- +1 positivo / -1 negativo / 0 neutro
    meta        TEXT    DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ts   ON samples (ts);
CREATE INDEX IF NOT EXISTS idx_kind ON samples (kind);
"""

_DDL_USED_IDX = "CREATE INDEX IF NOT EXISTS idx_used ON samples (used);"


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _init():
    with _lock, _conn() as c:
        c.executescript(_DDL_TABLE)
        # AG-06: migrate — add 'used' column if missing (existing DB from previous version)
        cols = [r[1] for r in c.execute("PRAGMA table_info(samples)").fetchall()]
        if "used" not in cols:
            c.execute("ALTER TABLE samples ADD COLUMN used INTEGER DEFAULT 0")
        c.executescript(_DDL_USED_IDX)


_init()


# ── Escritura ─────────────────────────────────────────────────────────────────

def record(
    kind: str,
    instruction: str,
    response: str,
    signal: float = 0.0,
    meta: dict | None = None,
) -> int:
    """Registra una muestra. Devuelve el id insertado."""
    ts = datetime.now(timezone.utc).isoformat()
    meta_str = json.dumps(meta or {}, ensure_ascii=False)
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO samples (ts, kind, instruction, response, signal, meta) VALUES (?,?,?,?,?,?)",
            (ts, kind, instruction, response, signal, meta_str),
        )
        return cur.lastrowid or 0


def record_interaction(user_msg: str, assistant_msg: str, system_prompt: str = "") -> int:
    """Captura una interacción chat normal."""
    return record("interaction", f"{system_prompt}\n\nUSER: {user_msg}".strip(), assistant_msg)


def record_approval(tool_name: str, args: dict, approved: bool, reason: str = "") -> int:
    """Captura una decisión de aprobación/rechazo de tool."""
    instruction = f"Herramienta solicitada: {tool_name}\nArgs: {json.dumps(args, ensure_ascii=False)[:500]}"
    response = "APROBADO" if approved else f"RECHAZADO: {reason}"
    signal = 1.0 if approved else -1.0
    return record("approval", instruction, response, signal, {"tool": tool_name, "approved": approved})


def record_feedback(instruction: str, response: str, positive: bool) -> int:
    """Captura feedback explícito del usuario (👍/👎)."""
    return record("feedback", instruction, response, 1.0 if positive else -1.0)


def record_event(event_type: str, description: str, decision: str, signal: float = 0.0) -> int:
    """Captura un evento de seguridad y la decisión tomada."""
    return record("event", f"Evento: {event_type}\n{description}", decision, signal,
                  {"event_type": event_type})


# ── AG-06: Marcar muestras como usadas en entrenamiento ──────────────────────

def mark_used(ids: list[int]) -> int:
    """Marca una lista de sample IDs como usados en entrenamiento. Retorna n filas afectadas."""
    if not ids:
        return 0
    with _lock, _conn() as c:
        placeholders = ",".join("?" for _ in ids)
        c.execute(f"UPDATE samples SET used=1 WHERE id IN ({placeholders})", ids)
        return len(ids)


# ── Lectura / stats ───────────────────────────────────────────────────────────

def count(kind: str | None = None) -> int:
    with _lock, _conn() as c:
        if kind:
            return c.execute("SELECT COUNT(*) FROM samples WHERE kind=?", (kind,)).fetchone()[0]
        return c.execute("SELECT COUNT(*) FROM samples").fetchone()[0]


def stats() -> dict:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT kind, COUNT(*) as n, AVG(signal) as avg_signal FROM samples GROUP BY kind"
        ).fetchall()
        total = c.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    return {
        "total": total,
        "by_kind": {r["kind"]: {"count": r["n"], "avg_signal": round(r["avg_signal"] or 0, 3)}
                    for r in rows},
    }


# ── K-05: Export QLoRA (JSONL chat format) ────────────────────────────────────

def export(
    path: str | Path | None = None,
    kind: str | None = None,
    min_signal: float | None = None,
    limit: int = 10_000,
) -> Path:
    """
    Exporta las muestras en formato JSONL compatible con fine-tuning Mistral/LLaMA.

    Cada línea es un objeto JSON con campo "messages" (lista de turns):
      {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

    Args:
        path: destino (default: data/training_export.jsonl)
        kind: filtrar por tipo ('interaction', 'approval', 'feedback', 'event')
        min_signal: solo incluir muestras con signal >= valor (ej: 0.0 excluye negativas)
        limit: máximo de muestras a exportar
    """
    out_path = Path(path) if path else _DB_PATH.parent / "training_export.jsonl"

    query = "SELECT * FROM samples WHERE 1=1"
    params: list = []
    if kind:
        query += " AND kind=?"
        params.append(kind)
    if min_signal is not None:
        query += " AND signal>=?"
        params.append(min_signal)
    query += " ORDER BY id LIMIT ?"
    params.append(limit)

    with _lock, _conn() as c:
        rows = c.execute(query, params).fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            instruction = row["instruction"] or ""
            response = row["response"] or ""
            # Intentar separar system del user si hay el patrón "\n\nUSER: "
            system_part = ""
            user_part = instruction
            if "\n\nUSER: " in instruction:
                system_part, user_part = instruction.split("\n\nUSER: ", 1)

            messages = []
            if system_part.strip():
                messages.append({"role": "system", "content": system_part.strip()})
            if user_part.strip():
                messages.append({"role": "user", "content": user_part.strip()})
            if response.strip():
                messages.append({"role": "assistant", "content": response.strip()})

            if len(messages) >= 2:
                # W-07: incluir señal normalizada como weight para fine-tuning
                signal = float(row["signal"] or 0.0)
                weight = max(0.0, (signal + 1.0) / 2.0)  # [-1,1] → [0,1]
                meta = json.loads(row["meta"] or "{}")
                entry: dict = {"messages": messages, "weight": round(weight, 4)}
                if meta.get("model"):
                    entry["model"] = meta["model"]
                if row["kind"]:
                    entry["kind"] = row["kind"]
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                written += 1

    return out_path
