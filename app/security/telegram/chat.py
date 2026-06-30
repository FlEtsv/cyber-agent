"""
B-05 + AR-06: Chat libre con el agente desde Telegram.

Cuando un usuario autorizado escribe texto libre (no comando), se lo pasamos
al brain_bridge → responde el modelo local cyberagent o Mistral según modo.
Mantiene historial por user_id en memoria (últimas 20 rondas).
"""
from __future__ import annotations

import threading
import time

_history: dict[int, list[dict]] = {}  # user_id → [{role, content}]
_lock = threading.Lock()
_MAX_HISTORY = 20


def _get_history(user_id: int) -> list[dict]:
    with _lock:
        return list(_history.get(user_id, []))


def _append(user_id: int, role: str, content: str) -> None:
    with _lock:
        hist = _history.setdefault(user_id, [])
        hist.append({"role": role, "content": content})
        if len(hist) > _MAX_HISTORY * 2:
            _history[user_id] = hist[-_MAX_HISTORY * 2 :]


def clear_history(user_id: int) -> None:
    with _lock:
        _history.pop(user_id, None)


def chat(user_id: int, text: str, username: str = "") -> str:
    """
    Procesa un mensaje libre del usuario y devuelve la respuesta del agente.
    """
    _append(user_id, "user", text)
    history = _get_history(user_id)

    try:
        from app.security.brain_bridge import chat as bb_chat
        reply = bb_chat(
            session_id=f"tg_{user_id}",
            message=text,
            history=history[:-1],  # sin el mensaje actual (ya lo pasamos en message)
        )
    except Exception as e:
        reply = f"Error al procesar: {e}"

    _append(user_id, "assistant", reply)
    return reply


def handle_reaction(user_id: int, message_id: int, emoji: str) -> None:
    """
    AR-07: Reacción 👍/👎 como feedback rápido → training_store.
    """
    signal = 1.0 if emoji in ("👍", "❤️", "🔥") else -1.0 if emoji in ("👎", "💩") else 0.0
    if signal == 0.0:
        return
    try:
        with _lock:
            hist = _history.get(user_id, [])
        # Buscar el último intercambio asistente
        for i in range(len(hist) - 1, -1, -1):
            if hist[i]["role"] == "assistant":
                instruction = hist[i - 1]["content"] if i > 0 else ""
                response = hist[i]["content"]
                from app.training_store import record
                record(
                    kind="telegram_reaction",
                    instruction=instruction,
                    response=response,
                    signal=signal,
                    meta={"user_id": user_id, "emoji": emoji, "message_id": message_id},
                )
                break
    except Exception:
        pass
