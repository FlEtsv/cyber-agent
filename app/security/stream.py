"""
N-02 + N-08: Proxy de stream de cámara en tiempo real.

Estrategia por disponibilidad:
1. go2rtc (si está corriendo en :1984) → WebRTC/HLS nativo
2. MJPEG vía ffmpeg (snapshot loop, sin plugins)
3. Snapshots periódicos vía /security/cameras/{cam_id}/snapshot como fallback

go2rtc es la solución recomendada para el stack Docker:
  docker run -p 1984:1984 alexxit/go2rtc

En el Dockerfile del stack ya está incluido.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_GO2RTC_HOST = os.environ.get("GO2RTC_HOST", "localhost")
_GO2RTC_PORT = int(os.environ.get("GO2RTC_PORT", "1984"))
_GO2RTC_URL = f"http://{_GO2RTC_HOST}:{_GO2RTC_PORT}"


# ── go2rtc ────────────────────────────────────────────────────────────────────

def stream_url(cam_id: str | int, source_url: str = "", protocol: str = "hls") -> str | None:
    """
    N-08: Devuelve la URL del stream para el protocolo solicitado.

    Prioridad:
    1. go2rtc si está disponible
    2. MJPEG endpoint local si hay ffmpeg
    3. None (fallback a snapshots)
    """
    cam_name = str(cam_id)

    if _go2rtc_available():
        if protocol == "webrtc":
            return f"{_GO2RTC_URL}/api/ws?src={cam_name}"
        elif protocol == "hls":
            return f"{_GO2RTC_URL}/api/stream.m3u8?src={cam_name}"
        elif protocol == "mjpeg":
            return f"{_GO2RTC_URL}/api/stream.mjpeg?src={cam_name}"

    # Fallback: MJPEG local
    if _ffmpeg_available() and source_url:
        return f"/security/cameras/{cam_name}/mjpeg"

    return None


def is_available() -> bool:
    return _go2rtc_available() or _ffmpeg_available()


def _go2rtc_available() -> bool:
    try:
        import httpx
        r = httpx.get(f"{_GO2RTC_URL}/api/status", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def _ffmpeg_available() -> bool:
    import shutil
    return bool(shutil.which("ffmpeg"))


# ── MJPEG server vía ffmpeg ───────────────────────────────────────────────────

_mjpeg_processes: dict[str, subprocess.Popen] = {}
_mjpeg_ports: dict[str, int] = {}
_port_counter = 8800


def start_mjpeg(cam_id: str, rtsp_url: str) -> int | None:
    """
    N-02: Inicia un stream MJPEG para una cámara RTSP.
    Retorna el puerto donde está disponible, o None si falla.
    """
    global _port_counter
    if cam_id in _mjpeg_processes:
        proc = _mjpeg_processes[cam_id]
        if proc.poll() is None:
            return _mjpeg_ports[cam_id]
        else:
            del _mjpeg_processes[cam_id]

    if not _ffmpeg_available():
        return None

    port = _port_counter
    _port_counter += 1

    import shutil
    ff = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ff, "-y",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-vf", "fps=5,scale=640:-1",
        "-c:v", "mjpeg",
        "-q:v", "5",
        "-f", "mpjpeg",
        f"tcp://0.0.0.0:{port}?listen=1",
    ]

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        _mjpeg_processes[cam_id] = proc
        _mjpeg_ports[cam_id] = port
        logger.info("stream: MJPEG %s iniciado en puerto %d", cam_id, port)
        return port
    except Exception as e:
        logger.error("stream.start_mjpeg: %s", e)
        return None


def stop_mjpeg(cam_id: str) -> bool:
    proc = _mjpeg_processes.pop(cam_id, None)
    if proc:
        proc.terminate()
        _mjpeg_ports.pop(cam_id, None)
        return True
    return False


# ── Snapshot-based pseudo-stream ─────────────────────────────────────────────

async def snapshot_stream_generator(cam_id: str, fps: float = 1.0):
    """
    N-02 fallback: stream como secuencia de snapshots (SSE data: image/jpeg base64).
    Intervalo = 1/fps segundos. Usado cuando no hay go2rtc ni MJPEG.
    """
    interval = 1.0 / max(fps, 0.1)
    while True:
        try:
            loop = asyncio.get_event_loop()
            image_b64 = await loop.run_in_executor(None, _get_snapshot, cam_id)
            if image_b64:
                yield f"data: {image_b64}\n\n"
        except Exception as e:
            logger.warning("stream.snapshot_stream_generator: %s", e)
        await asyncio.sleep(interval)


def _get_snapshot(cam_id: str) -> str:
    try:
        from app.security.camera import snapshot_by_name
        return snapshot_by_name(cam_id) or ""
    except Exception:
        return ""


# ── go2rtc: registrar una cámara ─────────────────────────────────────────────

def register_camera_in_go2rtc(cam_id: str, rtsp_url: str) -> bool:
    """Registra una cámara en go2rtc vía su API REST."""
    if not _go2rtc_available():
        return False
    try:
        import httpx
        r = httpx.post(
            f"{_GO2RTC_URL}/api/streams",
            json={cam_id: rtsp_url},
            timeout=5.0,
        )
        return r.status_code in (200, 201)
    except Exception as e:
        logger.warning("stream.register_camera_in_go2rtc: %s", e)
        return False
