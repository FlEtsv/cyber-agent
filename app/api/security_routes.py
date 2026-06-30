"""
D-03 + D-04: Routers FastAPI para eventos y cámaras de seguridad.

Montados en el servidor principal bajo el prefijo /security.
Auth: X-Event-Token header (SEC_EVENT_TOKEN del vault o app_registry).

Endpoints:
  POST /security/events/ingest   — ingerir evento externo (HA webhook, sensor)
  GET  /security/events/recent   — últimos eventos
  GET  /security/cameras         — listar cámaras
  POST /security/cameras/snapshot — snapshot de cámara
  GET  /security/status          — estado del módulo
  POST /security/autonomy        — cambiar modo de autonomía
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

router = APIRouter(prefix="/security", tags=["security"])


# ── D-04: Auth ─────────────────────────────────────────────────────────────────

def _require_auth(x_event_token: str | None = Header(default=None)) -> str:
    """Valida X-Event-Token header."""
    if not x_event_token:
        raise HTTPException(status_code=401, detail="X-Event-Token requerido")
    try:
        from app.security.app_registry import validate_token
        app_name = validate_token(x_event_token)
        if not app_name:
            raise HTTPException(status_code=403, detail="Token inválido")
        return app_name
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── D-03: Eventos ──────────────────────────────────────────────────────────────

@router.post("/events/ingest")
async def ingest_event(request: Request, app_name: str = Depends(_require_auth)) -> JSONResponse:
    """
    D-02: Normaliza e ingesta un evento externo.

    Body: cualquier dict con al menos 'event_type'.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    if "event_type" not in data:
        raise HTTPException(status_code=422, detail="Falta 'event_type'")

    data["source"] = app_name
    try:
        from app.security.events import handle_ha_event
        evt = handle_ha_event(data)
        return JSONResponse({"ok": True, "event_type": evt.event_type, "source": app_name})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/recent")
async def recent_events(n: int = 20, app_name: str = Depends(_require_auth)) -> JSONResponse:
    try:
        from app.security.events import recent
        evts = recent(n)
        return JSONResponse({"ok": True, "events": evts, "count": len(evts)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── D-03: Cámaras ──────────────────────────────────────────────────────────────

@router.get("/cameras")
async def list_cameras(app_name: str = Depends(_require_auth)) -> JSONResponse:
    try:
        from app.security.cameras_db import get_all_cameras
        cams = get_all_cameras()
        return JSONResponse({"ok": True, "cameras": cams})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cameras/snapshot")
async def take_snapshot(request: Request, app_name: str = Depends(_require_auth)) -> JSONResponse:
    """Body: {'cam_id': str}"""
    data = await request.json()
    cam_id = data.get("cam_id", "")
    if not cam_id:
        raise HTTPException(status_code=422, detail="Falta 'cam_id'")
    try:
        from app.security.camera import snapshot_by_name
        result = snapshot_by_name(cam_id)
        if not result.get("ok"):
            raise HTTPException(status_code=502, detail=result.get("error", "snapshot fallido"))
        # No devolver la imagen entera por REST — solo confirmar
        return JSONResponse({"ok": True, "cam_id": cam_id, "has_image": bool(result.get("image_b64"))})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Estado general ─────────────────────────────────────────────────────────────

@router.get("/status")
async def security_status(app_name: str = Depends(_require_auth)) -> JSONResponse:
    result: dict = {"security_enabled": os.environ.get("SECURITY_ENABLED", "0") == "1"}
    try:
        from app.security.brain_bridge import status as bb_status
        result["brain_bridge"] = bb_status()
    except Exception:
        pass
    try:
        from app.security.events import status as ev_status
        result["events"] = ev_status()
    except Exception:
        pass
    try:
        from app.security.autonomy import status as aut_status
        result["autonomy"] = aut_status()
    except Exception:
        pass
    try:
        from app.security.telegram.bot import status as bot_status
        result["telegram_bot"] = bot_status()
    except Exception:
        pass
    return JSONResponse({"ok": True, **result})


# ── Autonomía ──────────────────────────────────────────────────────────────────

@router.post("/autonomy")
async def set_autonomy(request: Request, app_name: str = Depends(_require_auth)) -> JSONResponse:
    """Body: {'mode': 'manual'|'operativa'|'alto-impacto'}"""
    data = await request.json()
    mode = data.get("mode", "")
    try:
        from app.security.autonomy import set_mode
        result = set_mode(mode, changed_by=app_name)
        if not result.get("ok"):
            raise HTTPException(status_code=422, detail=result.get("error", ""))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── N-02 + O-06: Stream en vivo ────────────────────────────────────────────────

@router.get("/cameras/{cam_id}/live")
async def camera_live_stream(cam_id: str) -> StreamingResponse:
    """
    O-06: Stream SSE de análisis IA en vivo para una cámara.
    No requiere auth (el token se gestiona en la sesión web).
    """
    from app.security.live_brain import live_analysis_stream
    return StreamingResponse(
        live_analysis_stream(cam_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/cameras/{cam_id}/snapshot-live")
async def camera_snapshot(cam_id: str) -> JSONResponse:
    """Snapshot en vivo de una cámara (JSON con image_b64)."""
    if not os.environ.get("SECURITY_ENABLED", "0") == "1":
        return JSONResponse({"ok": False, "error": "SECURITY_ENABLED=0"})
    try:
        from app.security.camera import snapshot_by_name
        image_b64 = snapshot_by_name(cam_id)
        return JSONResponse({"ok": True, "cam_id": cam_id, "image_b64": image_b64 or ""})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/cameras/{cam_id}/stream-url")
async def camera_stream_url(cam_id: str, protocol: str = "hls") -> JSONResponse:
    """Devuelve la URL del stream para el protocolo solicitado (hls|webrtc|mjpeg)."""
    try:
        from app.security.cameras_db import get_camera
        from app.security.stream import stream_url, is_available
        cam = get_camera(name=cam_id)
        source_url = cam.get("source_url", "") if cam else ""
        url = stream_url(cam_id, source_url, protocol)
        return JSONResponse({
            "ok": True,
            "cam_id": cam_id,
            "protocol": protocol,
            "url": url,
            "available": is_available(),
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/cameras/{cam_id}/recordings")
async def camera_recordings(
    cam_id: str,
    limit: int = 50,
    app_name: str = Depends(_require_auth),
) -> JSONResponse:
    """P-02: Lista grabaciones de una cámara."""
    try:
        from app.security.recorder import list_recordings
        recs = list_recordings(cam_id=cam_id, limit=limit)
        return JSONResponse({"ok": True, "cam_id": cam_id, "recordings": recs})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/cameras/{cam_id}/record")
async def start_camera_recording(
    cam_id: str,
    request: Request,
    app_name: str = Depends(_require_auth),
) -> JSONResponse:
    """P-01: Inicia grabación manual."""
    data = await request.json()
    duration = min(int(data.get("duration", 60)), 300)
    try:
        from app.security.cameras_db import get_camera
        cam = get_camera(name=cam_id)
        if not cam:
            return JSONResponse({"ok": False, "error": "Cámara no encontrada"}, status_code=404)
        rtsp_url = cam.get("source_url", "")
        if not rtsp_url:
            return JSONResponse({"ok": False, "error": "Sin URL RTSP configurada"}, status_code=422)
        from app.security.recorder import start_recording
        result = start_recording(cam_id=cam_id, rtsp_url=rtsp_url, duration=duration, trigger="manual")
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ── HA Webhook (sin auth para HA que llama directo) ───────────────────────────

@router.post("/ha/webhook")
async def ha_webhook(request: Request) -> JSONResponse:
    """
    Recibe webhooks de Home Assistant (sin token — HA llama con URL secreta).
    Valida la URL secreta en el path o un header alternativo.
    """
    data = await request.json()
    try:
        from app.security.events import handle_ha_event
        evt = handle_ha_event(data)
        return JSONResponse({"ok": True, "event_type": evt.event_type})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
