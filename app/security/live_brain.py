"""
O-02 + O-06: Stream de razonamiento IA en vivo por cámara.

Proporciona un endpoint SSE que emite eventos de análisis en tiempo real:
- snapshot cada N segundos
- análisis con Pixtral/local
- detecciones formateadas
- razonamiento en texto

El cliente (apps/web) conecta a /security/cameras/{cam_id}/live y recibe el stream.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Intervalo de análisis en vivo (segundos)
LIVE_INTERVAL = float(os.environ.get("LIVE_BRAIN_INTERVAL", "5"))
# Máximo de sesiones en vivo simultáneas
MAX_LIVE_SESSIONS = int(os.environ.get("MAX_LIVE_SESSIONS", "4"))

_active_sessions: dict[str, dict] = {}


def _security_enabled() -> bool:
    return os.environ.get("SECURITY_ENABLED", "0") == "1"


async def live_analysis_stream(cam_id: str) -> AsyncGenerator[str, None]:
    """
    O-06: Generator SSE de análisis en vivo para una cámara.

    Emite eventos:
    - snapshot: imagen actual (base64)
    - detection: objeto/persona/gato detectado
    - reasoning: razonamiento de la IA
    - status: estado del stream (activo/cooldown)
    - error: error en el análisis

    Uso en FastAPI:
        from fastapi.responses import StreamingResponse
        return StreamingResponse(live_analysis_stream(cam_id), media_type="text/event-stream")
    """
    if not _security_enabled():
        yield _sse_event("error", {"msg": "SECURITY_ENABLED=0"})
        return

    if len(_active_sessions) >= MAX_LIVE_SESSIONS:
        yield _sse_event("error", {"msg": "Máximo de sesiones activas alcanzado"})
        return

    session_id = f"{cam_id}_{int(time.time())}"
    _active_sessions[session_id] = {"cam_id": cam_id, "started": time.time()}

    try:
        yield _sse_event("status", {"cam_id": cam_id, "state": "active", "interval": LIVE_INTERVAL})

        while True:
            snap_result = await _get_snapshot(cam_id)
            if not snap_result.get("ok"):
                yield _sse_event("error", {"msg": snap_result.get("error", "No se pudo obtener snapshot")})
                await asyncio.sleep(LIVE_INTERVAL)
                continue

            image_b64 = snap_result.get("image_b64", "")

            # Emitir snapshot al cliente
            if image_b64:
                yield _sse_event("snapshot", {"cam_id": cam_id, "image_b64": image_b64, "ts": time.time()})

            # Analizar con IA
            analysis = await _analyze_frame(cam_id, image_b64)

            # Emitir razonamiento
            if analysis.get("description"):
                yield _sse_event("reasoning", {
                    "cam_id": cam_id,
                    "text": analysis["description"],
                    "threat_score": analysis.get("threat_score", 0.0),
                    "action": analysis.get("action", "ignore"),
                    "ts": time.time(),
                })

            # Emitir detecciones
            for det in analysis.get("detections", []):
                yield _sse_event("detection", {**det, "cam_id": cam_id, "ts": time.time()})

            await asyncio.sleep(LIVE_INTERVAL)

    except asyncio.CancelledError:
        logger.info("live_brain: stream cancelado para %s", cam_id)
    finally:
        _active_sessions.pop(session_id, None)
        yield _sse_event("status", {"cam_id": cam_id, "state": "stopped"})


async def _get_snapshot(cam_id: str) -> dict:
    """Obtiene snapshot de la cámara."""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _snapshot_sync, cam_id)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _snapshot_sync(cam_id: str) -> dict:
    try:
        from app.security.camera import snapshot_by_name
        img = snapshot_by_name(cam_id)
        if img:
            return {"ok": True, "image_b64": img}
        return {"ok": False, "error": "snapshot vacío"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _analyze_frame(cam_id: str, image_b64: str) -> dict:
    """Análisis asíncrono del frame."""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _analyze_sync, cam_id, image_b64)
        return result
    except Exception as e:
        logger.error("live_brain._analyze_frame: %s", e)
        return {"description": "", "threat_score": 0.0, "action": "ignore", "detections": []}


def _analyze_sync(cam_id: str, image_b64: str) -> dict:
    """Análisis síncrono usando brain_bridge."""
    try:
        from app.security.brain_bridge import analyze_image
        result = analyze_image(image_b64=image_b64, cam_id=cam_id)

        # Parsear detecciones del resultado
        detections = []
        if result.get("detected"):
            detections.append({
                "type": "object",
                "description": result.get("description", ""),
                "confidence": result.get("confidence", 0.5),
                "threat_score": result.get("threat_score", 0.0),
            })

        return {
            "description": result.get("description", ""),
            "threat_score": result.get("threat_score", 0.0),
            "action": result.get("action", "ignore"),
            "confidence": result.get("confidence", 0.5),
            "detections": detections,
        }
    except Exception as e:
        return {"description": f"Error: {e}", "threat_score": 0.0, "action": "ignore", "detections": []}


def _sse_event(event_type: str, data: dict) -> str:
    """Formatea un evento SSE."""
    import json
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def active_sessions() -> list[dict]:
    return list(_active_sessions.values())


def stop_session(cam_id: str) -> bool:
    """Para el stream de una cámara (marca para cancelar en el siguiente ciclo)."""
    keys = [k for k in _active_sessions if k.startswith(cam_id)]
    for k in keys:
        _active_sessions.pop(k, None)
    return bool(keys)
