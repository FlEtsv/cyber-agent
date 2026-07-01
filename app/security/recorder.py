"""
Y-03 + Y-07 + P-01..P-02: Video recorder con índice DB.

Graba clips de video desde RTSP con ffmpeg y los indexa en SQLite.
Retención automática: ver storage/retention.py (15 días legales).

DB: data/recordings.db
  - id, cam_id, started_at, ended_at, path, size_bytes, trigger, duration, thumb_b64
"""
from __future__ import annotations

import logging
import os
import sqlite3
import subprocess
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "recordings.db"
_CLIPS_DIR = Path(__file__).parent.parent.parent / "data" / "clips"
_lock = threading.Lock()
_active_recordings: dict[str, subprocess.Popen] = {}


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.execute(
        """CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cam_id TEXT,
            started_at REAL,
            ended_at REAL,
            path TEXT,
            size_bytes INTEGER,
            trigger TEXT,
            duration INTEGER,
            thumb_b64 TEXT
        )"""
    )
    c.commit()
    return c


# ── P-01: Grabar clip ─────────────────────────────────────────────────────────

def start_recording(
    cam_id: str,
    rtsp_url: str,
    duration: int = 60,
    trigger: str = "manual",
) -> dict:
    """
    P-01: Inicia grabación de un clip desde RTSP.

    Args:
        cam_id: ID de la cámara
        rtsp_url: URL RTSP
        duration: duración en segundos (máx 300)
        trigger: motivo (motion|manual|event|schedule)

    Returns:
        {'ok': bool, 'path': str, 'recording_id': int}
    """
    import shutil
    duration = min(duration, 300)
    ff = shutil.which("ffmpeg") or "ffmpeg"

    _CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = _CLIPS_DIR / f"{cam_id}_{ts}.mp4"

    started_at = time.time()

    # Registrar en DB antes de grabar (para poder hacer seguimiento)
    with _lock:
        c = _conn()
        cursor = c.execute(
            "INSERT INTO recordings (cam_id, started_at, path, trigger, duration) VALUES (?,?,?,?,?)",
            (cam_id, started_at, str(out_path), trigger, duration),
        )
        rec_id = cursor.lastrowid
        c.commit()
        c.close()

    # Grabar en background
    def _do_record():
        try:
            cmd = [
                ff, "-y",
                "-rtsp_transport", "tcp",
                "-i", rtsp_url,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-an",
                str(out_path),
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with _lock:
                _active_recordings[cam_id] = proc
            proc.wait(timeout=duration + 30)
        except Exception as e:
            logger.error("recorder: error grabando %s: %s", cam_id, e)
        finally:
            with _lock:
                _active_recordings.pop(cam_id, None)

            # Actualizar DB con tamaño y timestamp final
            ended_at = time.time()
            size = out_path.stat().st_size if out_path.exists() else 0
            thumb = _make_thumb(str(out_path))
            c = _conn()
            c.execute(
                "UPDATE recordings SET ended_at=?, size_bytes=?, thumb_b64=? WHERE id=?",
                (ended_at, size, thumb, rec_id),
            )
            c.commit()
            c.close()
            logger.info("recorder: clip guardado %s (%d bytes)", out_path, size)

    threading.Thread(target=_do_record, daemon=True).start()
    return {"ok": True, "path": str(out_path), "recording_id": rec_id}


def stop_recording(cam_id: str) -> bool:
    """Para una grabación activa."""
    with _lock:
        proc = _active_recordings.get(cam_id)
    if proc:
        proc.terminate()
        return True
    return False


def _make_thumb(video_path: str) -> str:
    """Genera thumbnail del primer frame (base64 JPEG)."""
    import base64, shutil
    ff = shutil.which("ffmpeg") or "ffmpeg"
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            out = tmp.name
        cmd = [ff, "-y", "-i", video_path, "-frames:v", "1", "-q:v", "5", out]
        r = subprocess.run(cmd, capture_output=True, timeout=10)
        if r.returncode == 0 and Path(out).exists():
            data = base64.b64encode(Path(out).read_bytes()).decode()
            return data
    except Exception:
        pass
    finally:
        try:
            os.unlink(out)
        except Exception:
            pass
    return ""


# ── P-02: Índice / consulta ───────────────────────────────────────────────────

def list_recordings(
    cam_id: str | None = None,
    limit: int = 50,
    since_ts: float | None = None,
) -> list[dict]:
    """
    Y-07: Lista grabaciones del índice DB.
    """
    c = _conn()
    query = "SELECT id, cam_id, started_at, ended_at, path, size_bytes, trigger, duration FROM recordings"
    params = []
    conditions = []
    if cam_id:
        conditions.append("cam_id=?")
        params.append(cam_id)
    if since_ts:
        conditions.append("started_at>=?")
        params.append(since_ts)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    rows = c.execute(query, params).fetchall()
    c.close()
    return [
        {
            "id": r[0], "cam_id": r[1], "started_at": r[2], "ended_at": r[3],
            "path": r[4], "size_bytes": r[5], "trigger": r[6], "duration": r[7],
        }
        for r in rows
    ]


def get_recording(rec_id: int) -> dict | None:
    """Recupera una grabación por ID, incluyendo thumbnail."""
    c = _conn()
    row = c.execute(
        "SELECT id, cam_id, started_at, ended_at, path, size_bytes, trigger, duration, thumb_b64 "
        "FROM recordings WHERE id=?",
        (rec_id,),
    ).fetchone()
    c.close()
    if not row:
        return None
    return {
        "id": row[0], "cam_id": row[1], "started_at": row[2], "ended_at": row[3],
        "path": row[4], "size_bytes": row[5], "trigger": row[6], "duration": row[7],
        "thumb_b64": row[8],
    }


def delete_recording(rec_id: int) -> bool:
    """Elimina una grabación del índice y del disco."""
    rec = get_recording(rec_id)
    if not rec:
        return False
    try:
        p = Path(rec["path"])
        if p.exists():
            p.unlink()
    except Exception as e:
        logger.warning("recorder.delete: %s", e)
    c = _conn()
    c.execute("DELETE FROM recordings WHERE id=?", (rec_id,))
    c.commit()
    c.close()
    return True


def cleanup_orphans() -> int:
    """Elimina del índice las entradas cuyo archivo ya no existe."""
    c = _conn()
    rows = c.execute("SELECT id, path FROM recordings").fetchall()
    deleted = 0
    for rid, path in rows:
        if path and not Path(path).exists():
            c.execute("DELETE FROM recordings WHERE id=?", (rid,))
            deleted += 1
    c.commit()
    c.close()
    return deleted
