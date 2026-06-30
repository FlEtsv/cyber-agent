"""
AJ-01: Gestión de mascotas registradas (fotos de referencia por gato).

Almacena en data/pets.db:
  - Nombre, especie, descripción
  - Múltiples fotos de referencia (embeddings)
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "pets.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS pets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    species     TEXT    NOT NULL DEFAULT 'cat',
    description TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS pet_refs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id      INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    image_b64   TEXT    NOT NULL,  -- foto de referencia en base64
    embedding   TEXT    DEFAULT NULL,  -- JSON float array, computed by reid.py
    ts          TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pet_refs_pet ON pet_refs (pet_id);
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_pet(name: str, species: str = "cat", description: str = "") -> dict:
    try:
        with _lock, _conn() as c:
            cur = c.execute(
                "INSERT INTO pets (name, species, description, created_at, updated_at) VALUES (?,?,?,?,?)",
                (name, species, description, _now(), _now()),
            )
            return {"ok": True, "id": cur.lastrowid}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"Ya existe una mascota con nombre '{name}'"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def add_reference_photo(pet_id: int, image_b64: str) -> dict:
    """Añade una foto de referencia para una mascota."""
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO pet_refs (pet_id, image_b64, ts) VALUES (?,?,?)",
            (pet_id, image_b64, _now()),
        )
        ref_id = cur.lastrowid
    # Intentar calcular el embedding
    try:
        from app.security.reid import extract_embedding
        emb = extract_embedding(image_b64)
        if emb:
            with _lock, _conn() as c:
                c.execute("UPDATE pet_refs SET embedding=? WHERE id=?",
                          (json.dumps(emb), ref_id))
    except Exception:
        pass
    return {"ok": True, "ref_id": ref_id}


def list_pets() -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM pets ORDER BY id").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            refs = c.execute(
                "SELECT id, ts FROM pet_refs WHERE pet_id=?", (r["id"],)
            ).fetchall()
            d["ref_count"] = len(refs)
            result.append(d)
    return result


def get_pet(pet_id: int) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute("SELECT * FROM pets WHERE id=?", (pet_id,)).fetchone()
        if not row:
            return None
        refs = c.execute(
            "SELECT id, embedding, ts FROM pet_refs WHERE pet_id=?", (pet_id,)
        ).fetchall()
        d = dict(row)
        d["refs"] = [{"id": r["id"], "ts": r["ts"],
                      "has_embedding": bool(r["embedding"])} for r in refs]
        return d


def get_embeddings(pet_id: int) -> list[list[float]]:
    """Retorna los embeddings de referencia de una mascota."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT embedding FROM pet_refs WHERE pet_id=? AND embedding IS NOT NULL", (pet_id,)
        ).fetchall()
    return [json.loads(r["embedding"]) for r in rows if r["embedding"]]


def delete_pet(pet_id: int) -> dict:
    with _lock, _conn() as c:
        c.execute("DELETE FROM pets WHERE id=?", (pet_id,))
    return {"ok": True, "id": pet_id}
