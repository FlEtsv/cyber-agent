"""
AK-06 + Q-03..Q-06: Zonas de vigilancia (polígonos peligrosos/seguros) por cámara.

Las zonas se definen como polígonos en coordenadas normalizadas (0-1).
El punto-en-polígono usa el algoritmo ray-casting.
Al solapar zonas, prevalece la de MAYOR riesgo.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "zones.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS zones (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    cam_id  TEXT    NOT NULL,
    name    TEXT    NOT NULL,
    type    TEXT    NOT NULL DEFAULT 'warning',  -- 'warning' | 'safe' | 'interest'
    points  TEXT    NOT NULL,  -- JSON [[x,y], ...] normalized 0-1
    color   TEXT    NOT NULL DEFAULT '#f85149',
    active  INTEGER NOT NULL DEFAULT 1,
    created TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_zones_cam ON zones (cam_id);
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


@dataclass
class Zone:
    id: int
    cam_id: str
    name: str
    type: str  # 'warning' | 'safe' | 'interest'
    points: list[tuple[float, float]]
    color: str
    active: bool

    @property
    def risk_level(self) -> int:
        return {"warning": 2, "interest": 1, "safe": 0}.get(self.type, 0)


def add_zone(
    cam_id: str,
    name: str,
    zone_type: str,
    points: list[tuple[float, float]],
    color: str = "#f85149",
) -> dict:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO zones (cam_id, name, type, points, color, active, created) VALUES (?,?,?,?,?,1,?)",
            (cam_id, name, zone_type, json.dumps(points), color, now),
        )
        return {"ok": True, "id": cur.lastrowid}


def list_zones(cam_id: str) -> list[Zone]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT * FROM zones WHERE cam_id=? AND active=1", (cam_id,)
        ).fetchall()
    return [
        Zone(
            id=r["id"],
            cam_id=r["cam_id"],
            name=r["name"],
            type=r["type"],
            points=json.loads(r["points"]),
            color=r["color"],
            active=bool(r["active"]),
        )
        for r in rows
    ]


def delete_zone(zone_id: int) -> dict:
    with _lock, _conn() as c:
        c.execute("UPDATE zones SET active=0 WHERE id=?", (zone_id,))
    return {"ok": True}


def point_in_zones(
    cx: float,
    cy: float,
    zones: list[Zone],
) -> Zone | None:
    """
    AK-06: Devuelve la zona de MAYOR riesgo que contiene el punto (cx, cy).
    Si no hay ninguna, devuelve None.
    """
    matched = [z for z in zones if _point_in_polygon(cx, cy, z.points)]
    if not matched:
        return None
    return max(matched, key=lambda z: z.risk_level)


def _point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting algorithm."""
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def check_track_zones(
    cam_id: str,
    cx: float,
    cy: float,
) -> dict:
    """
    Comprueba si el punto está en alguna zona y devuelve estado.
    Usado por el pipeline de visión para decidir si notificar.
    """
    zones = list_zones(cam_id)
    matched = point_in_zones(cx, cy, zones)
    if matched is None:
        return {"in_zone": False, "zone_name": None, "zone_type": None, "should_notify": False}
    should_notify = matched.type == "warning"
    return {
        "in_zone": True,
        "zone_name": matched.name,
        "zone_type": matched.type,
        "should_notify": should_notify,
    }
