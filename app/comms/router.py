"""
U-02 + U-03 + AO-02..AO-04: Router central de mensajes salientes con niveles de importancia.

Fuentes que pueden enviar:
  - Respuestas del agente (INFO)
  - Errores del sistema (ERROR)
  - Amenazas de seguridad (CRITICAL)
  - Herramientas completadas (SUCCESS)
  - Aprobaciones pendientes (WARNING)

Niveles: DEBUG < INFO < SUCCESS < WARNING < ERROR < CRITICAL
Solo pasan mensajes con nivel >= min_level configurado (defecto: INFO).
AO-02..04: integra topics, silencio en no-molestar, digest para BAJA/PERIÓDICA.
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

    AO-02..04: mensajes BAJA/PERIÓDICA van al digest; CRÍTICA nunca se silencia.
    AN-02: si hay topics configurados, envía al tema correcto por categoría.

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

    # AO-04: mensajes de baja importancia van al digest
    try:
        from app.comms.levels import from_int, GOES_TO_DIGEST
        sev = from_int(level)
        if sev in GOES_TO_DIGEST:
            from app.comms.digest import add_to_digest
            add_to_digest(title=title, body=body, source=source)
            return {"ok": True, "digest": True}
    except Exception:
        pass

    # AO-05: comprobar horario no-molestar
    try:
        from app.comms.rules import should_silence
        from app.comms.levels import from_int as _fi
        disable_notif = should_silence(_fi(level))
    except Exception:
        disable_notif = False

    used_emoji = emoji or _LEVEL_EMOJIS.get(level, "🔔")

    # AN-02: intentar envío por topic si disponible
    try:
        from app.comms.telegram_topics import has_forum_support, send_to_topic
        from app.secrets_vault import get_secret
        bot_token = get_secret("SEC_TELEGRAM_BOT_TOKEN") or get_secret("TELEGRAM_BOT_TOKEN")
        chat_id = get_secret("SEC_TELEGRAM_CHAT_ID") or get_secret("TELEGRAM_CHAT_ID")
        if bot_token and chat_id and has_forum_support():
            sent = send_to_topic(
                bot_token=bot_token,
                chat_id=chat_id,
                category=source,
                title=f"{used_emoji} {title}",
                body=body,
                disable_notification=disable_notif,
            )
            if sent:
                return {"ok": True, "topic": True}
    except Exception:
        pass

    # Fallback: envío directo por telegram
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


def send(title: str, body: str = "", severity=None, topic: str = "") -> dict:
    """AS-05: Alias de send_message con parámetros de nivel y topic."""
    from app.comms.levels import Severity
    level_map = {
        Severity.CRITICA: CRITICAL, Severity.ALTA: ERROR,
        Severity.MEDIA: WARNING, Severity.BAJA: SUCCESS,
        Severity.PERIODICA: INFO,
    }
    lvl = level_map.get(severity, INFO) if severity else INFO
    return send_message(title, body, level=lvl, source=topic or "system")


def get_config() -> list:
    """AS-01: Devuelve la configuración de canales activos."""
    channels = []
    try:
        from app.comms.telegram_topics import get_topics
        topics = get_topics()
        for name, thread_id in topics.items():
            channels.append({"id": name, "name": name, "topic_id": str(thread_id), "severity": "TODAS"})
    except Exception:
        channels.append({"id": "main", "name": "Canal principal", "topic_id": "0", "severity": "TODAS"})
    return channels
