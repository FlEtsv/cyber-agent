"""
AR-07: Reacciones de Telegram (👍/👎) → training_store.

El bot detecta reacciones emoji en mensajes que tienen un message_id registrado
y las convierte en señales de feedback positivo/negativo para entrenamiento.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

# msg_id → {chat_id, instruction, response} (para registrar con context)
_pending: dict[int, dict] = {}
_lock = threading.Lock()


def register_message(msg_id: int, chat_id: int, instruction: str, response: str):
    """Registrar un mensaje enviado como candidato a recibir feedback."""
    with _lock:
        _pending[msg_id] = {
            "chat_id": chat_id,
            "instruction": instruction,
            "response": response,
        }
        # Mantener máx 500 mensajes pendientes
        if len(_pending) > 500:
            oldest = next(iter(_pending))
            del _pending[oldest]


def handle_reaction(msg_id: int, emoji: str, user_id: int) -> bool:
    """
    Procesar una reacción Telegram (emoji) sobre un mensaje registrado.
    Retorna True si se registró como feedback.
    """
    with _lock:
        ctx = _pending.get(msg_id)
    if not ctx:
        return False

    positive_emojis = {"👍", "❤️", "🔥", "⭐", "🎉", "✅"}
    negative_emojis = {"👎", "💩", "😡", "❌", "🤮"}

    if emoji in positive_emojis:
        signal = 1.0
    elif emoji in negative_emojis:
        signal = -1.0
    else:
        return False

    try:
        from app.training_store import record
        record(
            kind="telegram_reaction",
            instruction=ctx["instruction"],
            response=ctx["response"],
            signal=signal,
            meta={"msg_id": msg_id, "emoji": emoji, "user_id": user_id},
        )
        logger.info("reactions: msg_id=%d emoji=%s signal=%.1f", msg_id, emoji, signal)
        return True
    except Exception as e:
        logger.error("reactions.handle_reaction: %s", e)
        return False


def pending_count() -> int:
    with _lock:
        return len(_pending)
