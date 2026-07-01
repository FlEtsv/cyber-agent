"""
N-07: CRUD de cámaras en SQLite.

Registra las cámaras del sistema con su tipo, fuente, ubicación, zonas y
tools asignadas. La tabla se crea automáticamente en data/cyberagent.db
(misma DB principal del proyecto).

Gateado: solo activo si SECURITY_ENABLED=1, pero el CRUD siempre está
disponible para poder pre-configurar las cámaras sin activar el módulo.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "cameras.db"
_lock = threading.Lock()

_DDL = """
CREATE TABLE IF NOT EXISTS cameras (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    kind        TEXT    NOT NULL DEFAULT 'interior',  -- 'exterior' | 'interior'
    source_type TEXT    NOT NULL DEFAULT 'ha',        -- 'ha' | 'rtsp' | 'usb'
    source_url  TEXT    NOT NULL DEFAULT '',          -- entity_id o URL RTSP
    location    TEXT    NOT NULL DEFAULT '',          -- descripción human-readable
    zones       TEXT    NOT NULL DEFAULT '[]',        -- JSON: list of zone dicts
    tools       TEXT    NOT NULL DEFAULT '[]',        -- JSON: list of tool names
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cam_kind ON cameras (kind);
CREATE INDEX IF NOT EXISTS idx_cam_enabled ON cameras (enabled);
CREATE TABLE IF NOT EXISTS camera_roi (
    cam_id      TEXT    PRIMARY KEY,
    roi_grid    TEXT    NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS discarded_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cam_id      TEXT    NOT NULL,
    ts          REAL    NOT NULL,
    label       TEXT    NOT NULL DEFAULT '',
    reason      TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_disc_cam ON discarded_events (cam_id, ts DESC);
"""


def get_db() -> sqlite3.Connection:
    """Devuelve una conexión a la DB de cámaras (para uso directo en endpoints)."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def log_discarded(cam_id: str, label: str, reason: str) -> None:
    """O-04: Registra una detección descartada por la IA."""
    import time
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO discarded_events(cam_id, ts, label, reason) VALUES(?,?,?,?)",
            (cam_id, time.time(), label, reason)
        )


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


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["zones"] = json.loads(d.get("zones") or "[]")
    d["tools"] = json.loads(d.get("tools") or "[]")
    d["enabled"] = bool(d["enabled"])
    return d


# ── CRUD ─────────────────────────────────────────────────────────────────────

def add_camera(
    name: str,
    kind: str = "interior",
    source_type: str = "ha",
    source_url: str = "",
    location: str = "",
    zones: list | None = None,
    tools: list | None = None,
) -> dict:
    """Añade una cámara. Devuelve {ok, id}."""
    if not name:
        return {"ok": False, "error": "name requerido"}
    if kind not in ("interior", "exterior"):
        return {"ok": False, "error": "kind debe ser 'interior' o 'exterior'"}
    now = _now()
    try:
        with _lock, _conn() as c:
            cur = c.execute(
                "INSERT INTO cameras (name, kind, source_type, source_url, location, zones, tools, enabled, created_at, updated_at) VALUES (?,?,?,?,?,?,?,1,?,?)",
                (name, kind, source_type, source_url, location,
                 json.dumps(zones or []), json.dumps(tools or []), now, now),
            )
            return {"ok": True, "id": cur.lastrowid}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"Ya existe una cámara con nombre '{name}'"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_camera(cam_id: int | None = None, name: str | None = None) -> dict | None:
    with _lock, _conn() as c:
        if cam_id is not None:
            row = c.execute("SELECT * FROM cameras WHERE id=?", (cam_id,)).fetchone()
        elif name:
            row = c.execute("SELECT * FROM cameras WHERE name=?", (name,)).fetchone()
        else:
            return None
    return _row_to_dict(row) if row else None


def list_cameras(kind: str | None = None, enabled_only: bool = False) -> list[dict]:
    query = "SELECT * FROM cameras WHERE 1=1"
    params: list = []
    if kind:
        query += " AND kind=?"
        params.append(kind)
    if enabled_only:
        query += " AND enabled=1"
    query += " ORDER BY id"
    with _lock, _conn() as c:
        rows = c.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_camera(cam_id: int, **fields) -> dict:
    allowed = {"name", "kind", "source_type", "source_url", "location",
               "zones", "tools", "enabled"}
    updates = {}
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k in ("zones", "tools") and isinstance(v, list):
            v = json.dumps(v)
        if k == "enabled":
            v = int(bool(v))
        updates[k] = v
    if not updates:
        return {"ok": False, "error": "Nada que actualizar"}
    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [cam_id]
    with _lock, _conn() as c:
        c.execute(f"UPDATE cameras SET {set_clause} WHERE id=?", vals)
    return {"ok": True, "id": cam_id}


def delete_camera(cam_id: int) -> dict:
    with _lock, _conn() as c:
        c.execute("DELETE FROM cameras WHERE id=?", (cam_id,))
    return {"ok": True, "id": cam_id}


def count() -> int:
    with _lock, _conn() as c:
        return c.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]


def get_camera_by_name(name: str) -> dict | None:
    """Alias para get_camera(name=name) — compatibilidad con camera.py."""
    return get_camera(name=name)


def get_all_cameras() -> list[dict]:
    """Alias para list_cameras() — compatibilidad con security_routes.py."""
    return list_cameras()


# ── S-10: Preconfigurar 3 cámaras de interior ────────────────────────────────

_DEFAULT_INTERIOR_CAMERAS = [
    {
        "name": "salon",
        "kind": "interior",
        "source_type": "ha",
        "source_url": "camera.salon",
        "location": "Salón principal — sofá + zona de paso",
    },
    {
        "name": "cocina",
        "kind": "interior",
        "source_type": "ha",
        "source_url": "camera.cocina",
        "location": "Cocina — zona de peligro para los gatos (fogones, enchufes)",
    },
    {
        "name": "dormitorio",
        "kind": "interior",
        "source_type": "ha",
        "source_url": "camera.dormitorio",
        "location": "Dormitorio — zona segura habitual de los gatos",
    },
]


def seed_interior_cameras(force: bool = False) -> dict:
    """
    S-10: Preconfigura las 3 cámaras de interior por defecto.

    Args:
        force: Si True, borra y recrea las cámaras aunque ya existan.

    Returns:
        dict con 'created', 'skipped', 'cameras'.
    """
    created = []
    skipped = []
    for spec in _DEFAULT_INTERIOR_CAMERAS:
        existing = get_camera(name=spec["name"])
        if existing and not force:
            skipped.append(spec["name"])
            continue
        if existing and force:
            delete_camera(existing["id"])
        result = add_camera(**spec)
        if result.get("ok"):
            created.append(spec["name"])
        else:
            skipped.append(f"{spec['name']} ({result.get('error', '?')})")
    return {
        "ok": True,
        "created": created,
        "skipped": skipped,
        "cameras": list_cameras(kind="interior"),
    }


def update_camera_context(cam_id_or_name: str, context: str) -> dict:
    """
    AW-06: Actualiza el contexto editable de una cámara (qué vigilar, qué se permite).
    Guarda en el campo 'location' como JSON extendido.
    """
    cam = get_camera(name=cam_id_or_name) if not str(cam_id_or_name).isdigit() else get_camera(cam_id=int(cam_id_or_name))
    if not cam:
        return {"ok": False, "error": f"Cámara '{cam_id_or_name}' no encontrada"}
    return update_camera(cam["id"], location=f"{cam.get('location', '')} | Contexto: {context}")
