"""
C-04..C-06: motion_tracker — loop de seguimiento, cooldown, notif inteligente.

Cuando se recibe un evento de movimiento (desde events.py o HA webhook):
1. Lanza un loop de seguimiento: N snapshots cada INTERVAL segundos.
2. Cooldown por cámara para evitar spam.
3. Notificaciones inteligentes: primer snapshot inmediato, followups si la amenaza persiste.
4. Duración máxima del seguimiento: MAX_DURATION segundos.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

INTERVAL = int(os.environ.get("MOTION_INTERVAL", "5"))       # segundos entre snapshots
MAX_DURATION = int(os.environ.get("MOTION_MAX_DURATION", "120"))  # segundos máx de seguimiento
COOLDOWN = int(os.environ.get("MOTION_COOLDOWN", "30"))      # cooldown por cámara tras fin


@dataclass
class MotionSession:
    cam_id: str
    started: float = field(default_factory=time.time)
    snapshots: int = 0
    active: bool = True
    last_snap: float = 0.0


_sessions: dict[str, MotionSession] = {}
_cooldowns: dict[str, float] = {}  # cam_id → ts fin cooldown
_lock = threading.Lock()


def _in_cooldown(cam_id: str) -> bool:
    ts = _cooldowns.get(cam_id, 0)
    return time.time() < ts


def _set_cooldown(cam_id: str) -> None:
    _cooldowns[cam_id] = time.time() + COOLDOWN


def trigger(cam_id: str, initial_snapshot: bool = True) -> bool:
    """
    C-04: Lanza un seguimiento para cam_id.
    Retorna False si ya hay sesión activa o en cooldown.
    """
    with _lock:
        if cam_id in _sessions and _sessions[cam_id].active:
            return False
        if _in_cooldown(cam_id):
            return False
        sess = MotionSession(cam_id=cam_id)
        _sessions[cam_id] = sess

    logger.info("motion: iniciando seguimiento %s", cam_id)
    t = threading.Thread(target=_tracking_loop, args=(cam_id, initial_snapshot), daemon=True)
    t.start()
    return True


def _tracking_loop(cam_id: str, initial_snapshot: bool) -> None:
    """C-04 + C-05 + C-06: loop de seguimiento con cooldown y notif inteligente."""
    from app.security.camera import snapshot_by_name
    from app.security.brain_bridge import analyze_image
    from app.security.anomaly import notify_anomalies

    start_ts = time.time()

    while True:
        with _lock:
            sess = _sessions.get(cam_id)
            if not sess or not sess.active:
                break

        elapsed = time.time() - start_ts

        # C-05: duración máxima
        if elapsed > MAX_DURATION:
            logger.info("motion: duración máxima alcanzada para %s", cam_id)
            break

        # Tomar snapshot
        result = snapshot_by_name(cam_id)
        if not result.get("ok"):
            logger.warning("motion: snapshot fallido %s: %s", cam_id, result.get("error"))
            time.sleep(INTERVAL)
            continue

        image_b64 = result["image_b64"]
        snap_num = 0
        with _lock:
            if cam_id in _sessions:
                _sessions[cam_id].snapshots += 1
                _sessions[cam_id].last_snap = time.time()
                snap_num = _sessions[cam_id].snapshots

        # C-06: análisis y notif inteligente
        try:
            analysis = analyze_image(image_b64, cam_id=cam_id)
            threat_score = analysis.get("threat_score", 0.0)
            description = analysis.get("description", "Movimiento detectado")

            # Primer snapshot: notificar siempre
            # Followups: solo si amenaza persiste (score > 0.5)
            if snap_num == 1 or threat_score > 0.5:
                _notify_followup(cam_id, image_b64, description, threat_score, snap_num)
        except Exception as e:
            logger.error("motion: análisis fallido: %s", e)
            if snap_num == 1:
                _notify_simple(cam_id, image_b64)

        time.sleep(INTERVAL)

    _end_session(cam_id)


def _notify_followup(
    cam_id: str, image_b64: str, description: str, threat: float, snap_num: int
) -> None:
    prefix = "🚨" if threat > 0.7 else ("⚠️" if threat > 0.4 else "👀")
    label = "ALERTA" if threat > 0.7 else ("Aviso" if threat > 0.4 else "Movimiento")
    title = f"{prefix} {label} — {cam_id}"
    body = description
    if snap_num > 1:
        title = f"📸 Seguimiento #{snap_num} — {cam_id}"

    from app.security.telegram.notify import broadcast
    from app.security.telegram.keyboards import security_keyboard
    import time as _t
    broadcast(
        title=title,
        body=body,
        emoji=prefix,
        keyboard=security_keyboard(cam_id=cam_id, event_id=str(int(_t.time()))),
        image_b64=image_b64,
    )


def _notify_simple(cam_id: str, image_b64: str) -> None:
    from app.security.telegram.notify import broadcast
    broadcast(title=f"📷 Movimiento — {cam_id}", emoji="📷", image_b64=image_b64)


def _end_session(cam_id: str) -> None:
    with _lock:
        sess = _sessions.pop(cam_id, None)
    if sess:
        _set_cooldown(cam_id)
        logger.info("motion: sesión terminada %s (%d snapshots)", cam_id, sess.snapshots)


def stop_tracking(cam_id: str) -> None:
    with _lock:
        sess = _sessions.get(cam_id)
        if sess:
            sess.active = False


def status() -> dict:
    with _lock:
        return {
            "active_sessions": list(_sessions.keys()),
            "cooldowns": {k: round(v - time.time(), 1) for k, v in _cooldowns.items() if v > time.time()},
        }
