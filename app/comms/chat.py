"""
AR-06: Chat libre con el AGENTE desde Telegram.

Recibe mensajes de texto del bot → los manda a brain_bridge → responde.
Solo para usuarios autorizados (admin/viewers).
"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

# Historial de sesión por chat_id (lista de turnos)
_sessions: dict[int, list[dict]] = defaultdict(list)
_lock = threading.Lock()
_MAX_HISTORY = 20


def handle_message(chat_id: int, text: str, user_name: str = "") -> str:
    """
    AR-06: Procesa un mensaje de texto libre → respuesta del agente.
    Retorna la respuesta como string (ya formateada para Telegram).
    """
    with _lock:
        history = list(_sessions[chat_id])

    history.append({"role": "user", "content": text})

    try:
        from app.security.brain_bridge import chat_with_agent
        reply = chat_with_agent(text, session_id=f"tg_{chat_id}", history=history)
    except Exception as e:
        logger.error("comms.chat: %s", e)
        reply = f"⚠️ Error al procesar: {e}"

    with _lock:
        _sessions[chat_id].append({"role": "user", "content": text})
        _sessions[chat_id].append({"role": "assistant", "content": reply})
        # Limitar historial
        if len(_sessions[chat_id]) > _MAX_HISTORY * 2:
            _sessions[chat_id] = _sessions[chat_id][-_MAX_HISTORY * 2:]

    return reply


def clear_session(chat_id: int):
    """Borrar historial de una sesión."""
    with _lock:
        _sessions.pop(chat_id, None)


def session_summary(chat_id: int) -> str:
    with _lock:
        turns = len(_sessions.get(chat_id, [])) // 2
    return f"Sesión activa: {turns} turnos"
