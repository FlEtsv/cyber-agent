"""
U-02 + U-03: Router central de mensajes salientes con niveles de importancia.

Fuentes que pueden enviar:
  - Respuestas del agente (INFO)
  - Errores del sistema (ERROR)
  - Amenazas de seguridad (CRITICAL)
  - Herramientas completadas (SUCCESS)
  - Aprobaciones pendientes (WARNING)

Niveles: DEBUG < INFO < SUCCESS < WARNING < ERROR < CRITICAL
Solo pasan mensajes con nivel >= min_level configurado (defecto: INFO).
"""
from __future__ import annotations

import threading

# Niveles de importancia
DEBUG    = 0
INFO     = 1
SUCCESS  = 2
WARNING  = 3
ERROR    = 4
CRITICAL = 5

_LEVEL_NAMES = {
    DEBUG: "debug", INFO: "info", SUCCESS: "success",
    WARNING: "warning", ERROR: "error", CRITICAL: "critical",
}
_LEVEL_EMOJIS = {
    DEBUG: "🔍", INFO: "ℹ️", SUCCESS: "✅", WARNING: "⚠️", ERROR: "❌", CRITICAL: "🚨",
}

_lock = threading.Lock()
_min_level: int = INFO
_muted: bool = False


def set_min_level(level: int) -> None:
    global _min_level
    with _lock:
        _min_level = level


def set_muted(muted: bool) -> None:
    global _muted
    with _lock:
        _muted = muted


def available() -> bool:
    from app.comms.telegram import available as _tg_avail
    return _tg_avail()


def send_message(
    title: str,
    body: str = "",
    level: int = INFO,
    source: str = "agent",
    emoji: str | None = None,
) -> dict:
    """
    Envía un mensaje por el canal configurado (Telegram) si el nivel lo permite.

    Args:
        title: título del mensaje (negrita)
        body: cuerpo del mensaje
        level: nivel de importancia (usa constantes: INFO, WARNING, ERROR, etc.)
        source: subsistema origen ('agent', 'security', 'supervisor', 'system')
        emoji: emoji override; si None usa el del nivel
    """
    with _lock:
        if _muted or level < _min_level:
            return {"ok": True, "skipped": True, "reason": "filtered"}

    used_emoji = emoji or _LEVEL_EMOJIS.get(level, "🔔")
    try:
        from app.comms.telegram import notify
        return notify(title=title, body=body, emoji=used_emoji)
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Helpers por tipo de mensaje ───────────────────────────────────────────────

def notify_agent_done(title: str, body: str = "") -> dict:
    return send_message(title, body, level=SUCCESS, source="agent", emoji="✅")


def notify_error(title: str, body: str = "") -> dict:
    return send_message(title, body, level=ERROR, source="system", emoji="❌")


def notify_threat(title: str, body: str = "") -> dict:
    return send_message(title, body, level=CRITICAL, source="security", emoji="🚨")


def notify_approval_needed(tool_name: str, preview: str = "") -> dict:
    return send_message(
        title=f"Aprobación requerida: {tool_name}",
        body=preview,
        level=WARNING,
        source="agent",
        emoji="⏳",
    )
