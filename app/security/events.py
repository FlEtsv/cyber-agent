"""
D-01 + D-02: event_store ring-buffer + event_handler.

Eventos entrantes: desde HA webhook, cámaras, sensores, motion_tracker.
Normalizados a CameraEvent / IncomingEvent antes de procesar.
Ring-buffer en memoria (últimos 500 eventos) + persistencia SQLite.

K-02: Cada decisión tomada queda en training_store.
"""
from __future__ import annotations

import collections
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_RING_SIZE = 500
_DB_PATH = Path("data/events.db")
_lock = threading.Lock()
_ring: collections.deque = collections.deque(maxlen=_RING_SIZE)
_subscribers: list[Callable] = []

__all__ = ["start", "stop", "status", "emit", "record_decision", "subscribe", "recent"]


# ── Modelos de datos ───────────────────────────────────────────────────────────

@dataclass
class CameraEvent:
    cam_id: str
    event_type: str                   # motion, person, pet, zone_breach, anomaly
    confidence: float = 1.0
    description: str = ""
    image_b64: str = ""
    ts: float = field(default_factory=time.time)
    source: str = "camera"            # camera | ha | sensor | manual


@dataclass
class IncomingEvent:
    """Evento genérico normalizado (HA webhook, sensores, etc.)."""
    event_type: str
    entity_id: str = ""
    state: str = ""
    payload: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    source: str = "unknown"


# ── SQLite store ───────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.execute(
        """CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            cam_id TEXT,
            description TEXT,
            source TEXT,
            confidence REAL,
            ts REAL,
            payload TEXT
        )"""
    )
    c.commit()
    return c


def _persist(evt: dict) -> None:
    try:
        import json
        c = _conn()
        c.execute(
            "INSERT INTO events (event_type, cam_id, description, source, confidence, ts, payload) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                evt.get("event_type", ""),
                evt.get("cam_id", evt.get("entity_id", "")),
                evt.get("description", ""),
                evt.get("source", ""),
                evt.get("confidence", 1.0),
                evt.get("ts", time.time()),
                json.dumps(evt.get("payload", {})),
            ),
        )
        c.commit()
        c.close()
    except Exception as e:
        logger.error("events._persist: %s", e)


# ── Ring buffer + emit ─────────────────────────────────────────────────────────

def emit(event_type: str, payload: dict | None = None) -> None:
    """D-02: Emite un evento al bus interno (ring-buffer + subscribers)."""
    evt = {
        "event_type": event_type,
        "ts": time.time(),
        **(payload or {}),
    }
    with _lock:
        _ring.append(evt)

    _persist(evt)

    for fn in list(_subscribers):
        try:
            fn(event_type, evt)
        except Exception as e:
            logger.error("events subscriber error: %s", e)


def subscribe(fn: Callable) -> None:
    """Registra un callback para recibir todos los eventos."""
    with _lock:
        _subscribers.append(fn)


def recent(n: int = 20, event_type: str | None = None, cam_id: str | None = None) -> list[dict]:
    """Retorna los últimos N eventos del ring-buffer, filtrando por tipo y/o cámara."""
    with _lock:
        evts = list(_ring)
    if event_type:
        evts = [e for e in evts if e.get("event_type") == event_type]
    if cam_id:
        evts = [e for e in evts if e.get("cam_id") == cam_id or e.get("camera_id") == cam_id]
    return evts[-n:]


# ── D-02: Normalización desde HA webhook ──────────────────────────────────────

def handle_ha_event(data: dict) -> IncomingEvent:
    """
    Normaliza payload de un webhook de HA a IncomingEvent y lo emite.
    """
    evt = IncomingEvent(
        event_type=data.get("event_type", data.get("type", "ha_event")),
        entity_id=data.get("entity_id", ""),
        state=data.get("new_state", {}).get("state", "") if isinstance(data.get("new_state"), dict) else "",
        payload=data,
        source="ha",
    )
    emit(evt.event_type, {**asdict(evt), "source": "ha"})

    # Disparar motion tracking si es evento de movimiento
    if "motion" in evt.event_type.lower() or evt.state in ("detected", "on"):
        cam_id = evt.entity_id.replace("binary_sensor.", "camera.").replace("_motion", "")
        try:
            from app.security.motion import trigger
            trigger(cam_id)
        except Exception:
            pass

    return evt


def handle_camera_event(cam_id: str, event_type: str, **kwargs) -> CameraEvent:
    """
    Crea y emite un CameraEvent.
    """
    evt = CameraEvent(cam_id=cam_id, event_type=event_type, **kwargs)
    emit(event_type, {**asdict(evt), "cam_id": cam_id})
    return evt


# ── K-02: record_decision ─────────────────────────────────────────────────────

def record_decision(
    event_type: str,
    description: str,
    decision: str,
    outcome: str = "",
    signal: float = 0.0,
) -> int:
    full_desc = f"Evento: {event_type}\n{description}"
    full_decision = decision + (f"\nResultado: {outcome}" if outcome else "")
    try:
        from app.training_store import record
        return record(
            kind="security_decision",
            instruction=full_desc,
            response=full_decision,
            signal=signal,
            meta={"event_type": event_type, "outcome": outcome},
        )
    except Exception:
        return 0


# ── Ciclo de vida ──────────────────────────────────────────────────────────────

_running = False


def start() -> None:
    global _running
    if os.environ.get("SECURITY_ENABLED", "0") != "1":
        return
    _running = True
    logger.info("events: motor iniciado")


def stop() -> None:
    global _running
    _running = False


def status() -> dict:
    with _lock:
        ring_size = len(_ring)
    return {
        "enabled": _running,
        "ring_size": ring_size,
        "subscribers": len(_subscribers),
    }
