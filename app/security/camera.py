"""
C-01..C-03: camera_client — snapshot HA, frame RTSP (ffmpeg), clip corto (ffmpeg).

Tres métodos de captura, en orden de preferencia:
  1. Home Assistant camera.snapshot (HA entity → imagen JPEG)
  2. RTSP → ffmpeg → frame JPEG
  3. ffmpeg clip corto (.mp4 30s)

Todo gateado por SECURITY_ENABLED. Secretos vía vault (SEC_HA_URL, SEC_HA_TOKEN).
"""
from __future__ import annotations

import base64
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

__all__ = ["snapshot", "snapshot_rtsp", "record_clip", "snapshot_by_name", "start", "stop", "status"]


# ── Configuración ─────────────────────────────────────────────────────────────

def _ha_cfg() -> tuple[str | None, str | None]:
    try:
        from app.secrets_vault import get_secret
        url = get_secret("SEC_HA_URL") or get_secret("HA_URL")
        token = get_secret("SEC_HA_TOKEN") or get_secret("HA_TOKEN")
        return url, token
    except Exception:
        return None, None


def _ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


# ── C-01: Snapshot vía Home Assistant ─────────────────────────────────────────

def snapshot(entity_id: str) -> dict:
    """
    C-01: Captura snapshot de una cámara HA.

    Args:
        entity_id: entity_id de la cámara en HA (ej. 'camera.entrada')

    Returns:
        {'ok': bool, 'image_b64': str, 'entity': str}
    """
    ha_url, ha_token = _ha_cfg()
    if not ha_url or not ha_token:
        return {"ok": False, "error": "HA no configurado (SEC_HA_URL / SEC_HA_TOKEN)"}

    # 1. Pedir snapshot a HA
    try:
        r = httpx.post(
            f"{ha_url.rstrip('/')}/api/services/camera/snapshot",
            headers={"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"},
            json={"entity_id": entity_id},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            return {"ok": False, "error": f"HA snapshot status {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    # 2. Descargar la imagen de la entidad cámara
    try:
        r2 = httpx.get(
            f"{ha_url.rstrip('/')}/api/camera_proxy/{entity_id}",
            headers={"Authorization": f"Bearer {ha_token}"},
            timeout=15,
        )
        if r2.status_code != 200:
            return {"ok": False, "error": f"proxy image status {r2.status_code}"}
        image_b64 = base64.b64encode(r2.content).decode()
        return {"ok": True, "image_b64": image_b64, "entity": entity_id, "source": "ha"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── C-02: Frame RTSP con ffmpeg ────────────────────────────────────────────────

def snapshot_rtsp(rtsp_url: str) -> dict:
    """
    C-02: Captura un frame desde un stream RTSP usando ffmpeg.

    Args:
        rtsp_url: URL completa (rtsp://user:pass@ip:port/path)

    Returns:
        {'ok': bool, 'image_b64': str}
    """
    ff = _ffmpeg()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        out_path = tmp.name

    try:
        cmd = [
            ff, "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-frames:v", "1",
            "-q:v", "2",
            out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=20)
        if result.returncode != 0 or not Path(out_path).exists():
            return {"ok": False, "error": f"ffmpeg error: {result.stderr.decode(errors='replace')[:300]}"}
        with open(out_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        return {"ok": True, "image_b64": image_b64, "source": "rtsp"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            os.unlink(out_path)
        except Exception:
            pass


# ── C-03: Clip corto con ffmpeg ────────────────────────────────────────────────

def record_clip(rtsp_url: str, duration: int = 30, output_path: str | None = None) -> dict:
    """
    C-03: Graba un clip corto desde RTSP.

    Args:
        rtsp_url: URL RTSP
        duration: duración en segundos (máx 120)
        output_path: ruta de salida (auto-generada si None)

    Returns:
        {'ok': bool, 'path': str, 'size_bytes': int}
    """
    duration = min(duration, 120)
    ff = _ffmpeg()

    if output_path is None:
        import time
        clips_dir = Path("data/clips")
        clips_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = str(clips_dir / f"clip_{ts}.mp4")

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
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=duration + 30)
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr.decode(errors="replace")[:300]}
        size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
        return {"ok": True, "path": output_path, "size_bytes": size}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── C-07: snapshot por nombre (busca en cameras_db) ───────────────────────────

def snapshot_by_name(name: str) -> dict:
    """
    Captura un snapshot de la cámara con el nombre dado.
    Busca en cameras_db la fuente (HA entity o RTSP URL).
    """
    try:
        from app.security.cameras_db import get_camera_by_name
        cam = get_camera_by_name(name)
        if not cam:
            return {"ok": False, "error": f"Cámara '{name}' no encontrada"}

        source = cam.get("source_type", "ha")
        if source == "rtsp":
            return snapshot_rtsp(cam["rtsp_url"])
        else:
            return snapshot(cam["entity_id"])
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Stubs de ciclo de vida ─────────────────────────────────────────────────────

def start() -> None:
    if os.environ.get("SECURITY_ENABLED", "0") != "1":
        return
    logger.info("camera_client: listo")


def stop() -> None:
    pass


def status() -> dict:
    ha_url, ha_token = _ha_cfg()
    return {
        "enabled": os.environ.get("SECURITY_ENABLED", "0") == "1",
        "ha_configured": bool(ha_url and ha_token),
        "ffmpeg": bool(shutil.which("ffmpeg")),
    }
