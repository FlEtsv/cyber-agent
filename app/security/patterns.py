"""
AK-05 + AL-04..AL-06: Aprendizaje de patrones por gato.

Detecta:
- Lugares de descanso (zona con permanencia > threshold)
- Rutas/zonas habituales por hora
- Refinamiento individual sobre priors de especie
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "patterns.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS rest_places (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id      INTEGER,
    label       TEXT    NOT NULL DEFAULT 'cat',
    cam_id      TEXT    NOT NULL,
    cx          REAL    NOT NULL,
    cy          REAL    NOT NULL,
    radius      REAL    NOT NULL DEFAULT 0.05,
    visit_count INTEGER NOT NULL DEFAULT 1,
    total_secs  REAL    NOT NULL DEFAULT 0,
    last_seen   TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS hourly_zones (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id  INTEGER,
    label   TEXT NOT NULL DEFAULT 'cat',
    cam_id  TEXT NOT NULL,
    hour    INTEGER NOT NULL,   -- 0-23
    cx      REAL NOT NULL,
    cy      REAL NOT NULL,
    count   INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_rest_pet ON rest_places (pet_id, cam_id);
CREATE INDEX IF NOT EXISTS idx_hourly_pet ON hourly_zones (pet_id, cam_id, hour);
"""

_REST_RADIUS = 0.08     # radio de clustering de lugares de descanso
_REST_MIN_SECS = 30.0   # segundos mínimos para considerar "descanso"


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _init():
    with _lock, _conn() as c:
        c.executescript(_DDL)


_init()


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def record_position(
    cam_id: str,
    cx: float,
    cy: float,
    pet_id: int | None = None,
    label: str = "cat",
    dwell_secs: float = 0.0,
):
    """
    AK-05: Registra una posición y detecta si es un lugar de descanso.
    Llama a esto con la duración desde la última posición (dwell_secs).
    """
    hour = int(time.localtime().tm_hour)

    with _lock, _conn() as c:
        # Lugar de descanso: buscar cluster cercano
        rows = c.execute(
            "SELECT id, cx, cy, visit_count, total_secs FROM rest_places WHERE cam_id=? AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL))",
            (cam_id, pet_id, pet_id),
        ).fetchall()

        nearest = None
        min_dist = _REST_RADIUS
        for r in rows:
            dist = ((r["cx"] - cx) ** 2 + (r["cy"] - cy) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                nearest = r

        if nearest:
            new_total = nearest["total_secs"] + dwell_secs
            c.execute(
                "UPDATE rest_places SET visit_count=?, total_secs=?, last_seen=? WHERE id=?",
                (nearest["visit_count"] + 1, new_total, _now_iso(), nearest["id"]),
            )
        elif dwell_secs > _REST_MIN_SECS:
            c.execute(
                "INSERT INTO rest_places (pet_id, label, cam_id, cx, cy, radius, visit_count, total_secs, last_seen) VALUES (?,?,?,?,?,?,1,?,?)",
                (pet_id, label, cam_id, cx, cy, _REST_RADIUS, dwell_secs, _now_iso()),
            )

        # Zona horaria habitual
        rows_h = c.execute(
            "SELECT id, cx, cy, count FROM hourly_zones WHERE cam_id=? AND hour=? AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL))",
            (cam_id, hour, pet_id, pet_id),
        ).fetchall()
        nearest_h = None
        min_d = 0.15
        for r in rows_h:
            d = ((r["cx"] - cx) ** 2 + (r["cy"] - cy) ** 2) ** 0.5
            if d < min_d:
                min_d = d
                nearest_h = r
        if nearest_h:
            c.execute("UPDATE hourly_zones SET count=?, cx=?, cy=? WHERE id=?",
                      (nearest_h["count"] + 1,
                       (nearest_h["cx"] * nearest_h["count"] + cx) / (nearest_h["count"] + 1),
                       (nearest_h["cy"] * nearest_h["count"] + cy) / (nearest_h["count"] + 1),
                       nearest_h["id"]))
        else:
            c.execute(
                "INSERT INTO hourly_zones (pet_id, label, cam_id, hour, cx, cy, count) VALUES (?,?,?,?,?,?,1)",
                (pet_id, label, cam_id, hour, cx, cy),
            )


def rest_places(
    cam_id: str,
    pet_id: int | None = None,
    min_visits: int = 3,
    min_secs: float = _REST_MIN_SECS,
) -> list[dict]:
    """AK-05: Devuelve los lugares de descanso detectados."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM rest_places WHERE cam_id=? AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL)) AND visit_count>=? AND total_secs>=?",
            (cam_id, pet_id, pet_id, min_visits, min_secs),
        ).fetchall()
    return [dict(r) for r in rows]


def typical_zones_by_hour(
    cam_id: str,
    hour: int,
    pet_id: int | None = None,
) -> list[dict]:
    """AL-04: Devuelve zonas habituales para una hora del día."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM hourly_zones WHERE cam_id=? AND hour=? AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL)) ORDER BY count DESC",
            (cam_id, hour, pet_id, pet_id),
        ).fetchall()
    return [dict(r) for r in rows]
