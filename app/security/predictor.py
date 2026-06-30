"""
AL-01 + AL-02: Predictor de movimiento por gato.

Predice la siguiente posición/zona dada la posición actual, hora y patrón aprendido.
Bucle auto-feedback: predice → espera → compara con real → señal +/- al training_store.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "predictor.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id      INTEGER,
    label       TEXT    NOT NULL DEFAULT 'cat',
    cam_id      TEXT    NOT NULL,
    ts_pred     TEXT    NOT NULL,  -- cuándo se hizo la predicción
    ts_verify   TEXT,              -- cuándo se verificó (NULL = pendiente)
    pred_cx     REAL    NOT NULL,
    pred_cy     REAL    NOT NULL,
    real_cx     REAL,
    real_cy     REAL,
    hit         INTEGER,           -- 1=acertó, 0=falló, NULL=pendiente
    error_dist  REAL               -- distancia error euclidea
);
CREATE INDEX IF NOT EXISTS idx_pred_pet ON predictions (pet_id, cam_id);
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
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def predict_next(
    cam_id: str,
    cx: float,
    cy: float,
    pet_id: int | None = None,
    label: str = "cat",
) -> tuple[float, float]:
    """
    AL-01: Predice la siguiente posición más probable.

    Lógica:
    1. Busca zonas habituales para la hora actual
    2. Devuelve el centroide más frecuente más cercano a la posición actual
    3. Si no hay patrón, usa prior de especie (inercia)
    """
    from app.security.patterns import typical_zones_by_hour
    from app.security.species_priors import get_priors

    hour = int(time.localtime().tm_hour)
    zones = typical_zones_by_hour(cam_id, hour, pet_id)

    if zones:
        # Ordenar por frecuencia y distancia combinada
        def score(z):
            dist = ((z["cx"] - cx) ** 2 + (z["cy"] - cy) ** 2) ** 0.5
            return z["count"] / (1 + dist * 5)
        best = max(zones, key=score)
        pred_cx = best["cx"] * 0.6 + cx * 0.4
        pred_cy = best["cy"] * 0.6 + cy * 0.4
    else:
        priors = get_priors(label)
        max_disp = priors["top_speed_norm"]
        pred_cx = max(0.0, min(1.0, cx + 0.0))  # inercia
        pred_cy = max(0.0, min(1.0, cy + 0.0))

    # Guardar predicción pendiente de verificación
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO predictions (pet_id, label, cam_id, ts_pred, pred_cx, pred_cy) VALUES (?,?,?,?,?,?)",
            (pet_id, label, cam_id, _now(), pred_cx, pred_cy),
        )

    return (pred_cx, pred_cy)


def verify_prediction(
    cam_id: str,
    real_cx: float,
    real_cy: float,
    pet_id: int | None = None,
    hit_threshold: float = 0.1,
):
    """
    AL-02: Verifica la predicción más reciente pendiente para este (cam_id, pet_id).
    Calcula el error y registra en training_store con señal +/-1.
    """
    with _lock, _conn() as c:
        row = c.execute(
            "SELECT id, pred_cx, pred_cy FROM predictions WHERE cam_id=? AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL)) AND hit IS NULL ORDER BY id DESC LIMIT 1",
            (cam_id, pet_id, pet_id),
        ).fetchone()
        if not row:
            return

        dist = ((row["pred_cx"] - real_cx) ** 2 + (row["pred_cy"] - real_cy) ** 2) ** 0.5
        hit = 1 if dist <= hit_threshold else 0
        c.execute(
            "UPDATE predictions SET ts_verify=?, real_cx=?, real_cy=?, hit=?, error_dist=? WHERE id=?",
            (_now(), real_cx, real_cy, hit, dist, row["id"]),
        )

    # Señal al training_store (AL-02)
    try:
        from app.training_store import record
        instruction = f"Predicción de posición gato cam={cam_id} desde ({row['pred_cx']:.2f},{row['pred_cy']:.2f})"
        response = f"Posición real: ({real_cx:.2f},{real_cy:.2f}). Error: {dist:.3f}"
        signal = 1.0 if hit else -0.5
        record("event", instruction, response, signal, {"cam_id": cam_id, "pet_id": pet_id, "kind": "prediction"})
    except Exception:
        pass


def prediction_stats(cam_id: str, pet_id: int | None = None) -> dict:
    """AL-03: Estadísticas de aciertos/fallos del predictor."""
    with _lock, _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE cam_id=? AND hit IS NOT NULL AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL))",
            (cam_id, pet_id, pet_id),
        ).fetchone()[0]
        hits = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE cam_id=? AND hit=1 AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL))",
            (cam_id, pet_id, pet_id),
        ).fetchone()[0]
        avg_err = c.execute(
            "SELECT AVG(error_dist) FROM predictions WHERE cam_id=? AND error_dist IS NOT NULL AND (pet_id=? OR (pet_id IS NULL AND ? IS NULL))",
            (cam_id, pet_id, pet_id),
        ).fetchone()[0]
    return {
        "total": total,
        "hits": hits,
        "accuracy": round(hits / total, 3) if total > 0 else None,
        "avg_error": round(avg_err, 4) if avg_err else None,
    }
