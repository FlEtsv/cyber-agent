"""
AX-01..AX-04: Límites legales de disuasión + cooldown anti-abuso.

Reglas:
  AX-01: Nivel 5 (SIREN) requiere confirmación humana (nunca automático).
  AX-02: Máx 3 activaciones de AUDIO_WARN por hora por cámara.
  AX-03: NARRATE incluye aviso legal ("grabación en curso").
  AX-04: Cooldown global 5 min entre escaladas.

Toda acción se registra en data/deterrence_log.jsonl para auditoría.
"""
from __future__ import annotations

import json
import logging
import time
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_LOG_PATH = Path("data/deterrence_log.jsonl")
_lock = threading.Lock()

# Contadores por cámara: cam_id → {intent → [timestamps]}
_counters: dict[str, dict[str, list[float]]] = {}
_last_escalate: dict[str, float] = {}  # cam_id → ts

# Límites
MAX_AUDIO_WARN_PER_HOUR = 3
ESCALATE_COOLDOWN = 300  # segundos entre escaladas por cámara
SIREN_REQUIRES_HUMAN = True  # AX-01


def check_and_record(cam_id: str, intent: str, level: int) -> dict:
    """
    Verifica que la acción de disuasión está dentro de los límites legales.

    Returns:
        {'ok': bool, 'reason': str}  — ok=False bloquea la acción
    """
    now = time.time()

    # AX-01: SIREN nunca automático
    if intent == "SIREN" and SIREN_REQUIRES_HUMAN:
        from app.security.autonomy import get_mode
        if get_mode() == "alto-impacto":
            pass  # permitir solo en alto-impacto con aprobación previa
        else:
            return {"ok": False, "reason": "SIREN requiere aprobación humana (AX-01)"}

    # AX-02: límite de audio por hora
    if intent == "AUDIO_WARN":
        with _lock:
            cam_counts = _counters.setdefault(cam_id, {})
            times = cam_counts.setdefault("AUDIO_WARN", [])
            # Limpiar timestamps > 1h
            times[:] = [t for t in times if now - t < 3600]
            if len(times) >= MAX_AUDIO_WARN_PER_HOUR:
                return {
                    "ok": False,
                    "reason": f"Límite de {MAX_AUDIO_WARN_PER_HOUR} alertas de audio por hora (AX-02)",
                }
            times.append(now)

    # AX-04: cooldown entre escaladas
    if level >= 3:
        with _lock:
            last = _last_escalate.get(cam_id, 0)
            if now - last < ESCALATE_COOLDOWN:
                remaining = int(ESCALATE_COOLDOWN - (now - last))
                return {"ok": False, "reason": f"Cooldown: espera {remaining}s antes de escalar (AX-04)"}
            _last_escalate[cam_id] = now

    # Registrar para auditoría
    _audit_log(cam_id, intent, level)

    return {"ok": True, "reason": ""}


def legal_notice_text() -> str:
    """AX-03: Texto de aviso legal para incluir en NARRATE."""
    return "Atención: esta propiedad cuenta con sistema de videovigilancia activo. Su presencia ha sido registrada."


def _audit_log(cam_id: str, intent: str, level: int) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.time(),
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cam_id": cam_id,
            "intent": intent,
            "level": level,
        }
        with _lock:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error("legal_limits._audit_log: %s", e)


def get_audit_log(n: int = 50) -> list[dict]:
    """Lee las últimas N entradas del log de auditoría."""
    entries = []
    try:
        if _LOG_PATH.exists():
            lines = _LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
            for line in lines[-n:]:
                entries.append(json.loads(line))
    except Exception:
        pass
    return entries


def reset_counters(cam_id: str) -> None:
    """Resetea los contadores de una cámara (para testing)."""
    with _lock:
        _counters.pop(cam_id, None)
        _last_escalate.pop(cam_id, None)
