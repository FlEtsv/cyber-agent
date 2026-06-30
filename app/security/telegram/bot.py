"""
B-01: Bot Telegram con long-polling (httpx, sin python-telegram-bot).

Gateado por SECURITY_ENABLED. Se ejecuta en un thread bajo el supervisor.
Loop:
  1. getUpdates (long-polling, timeout=30s)
  2. Por cada update:
     - Si es /comando → dispatch en commands.py
     - Si es texto libre + usuario autorizado → chat.py (brain_bridge)
     - Si es callback_query → callbacks.py
     - Si es mensaje de voz → ignorar (no implementado)
"""
from __future__ import annotations

import logging
import os
import threading
import time

import httpx

logger = logging.getLogger(__name__)

_running = False
_thread: threading.Thread | None = None
_offset: int = 0


def _token() -> str | None:
    try:
        from app.secrets_vault import get_secret
        return get_secret("SEC_TELEGRAM_BOT_TOKEN")
    except Exception:
        return os.environ.get("SEC_TELEGRAM_BOT_TOKEN")


def _api(token: str, method: str, **kwargs) -> dict:
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=kwargs,
            timeout=35,
        )
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _get_updates(token: str, offset: int) -> list[dict]:
    resp = _api(token, "getUpdates", offset=offset, timeout=30, allowed_updates=["message", "callback_query"])
    if resp.get("ok"):
        return resp.get("result", [])
    return []


def _handle_update(token: str, update: dict) -> None:
    global _offset
    uid = update["update_id"]
    _offset = uid + 1

    if "callback_query" in update:
        _handle_callback(token, update["callback_query"])
        return

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    user = msg.get("from", {})
    user_id = user.get("id", 0)
    username = user.get("username", "")
    text = msg.get("text", "")

    if not text:
        return  # ignorar stickers, fotos, etc.

    from app.security.telegram.commands import dispatch
    from app.security.telegram.auth import is_authorized_user, is_challenge_pending, resolve_challenge
    from app.security.telegram.notify import send_to_user

    # Intentar resolver challenge TOTP si hay código de 6 dígitos
    if text.strip().isdigit() and len(text.strip()) == 6 and is_challenge_pending(user_id):
        if resolve_challenge(user_id, text.strip(), username):
            send_to_user(user_id, "✅ Autenticado. Bienvenido a CyberAgent.")
        else:
            send_to_user(user_id, "❌ Código incorrecto. Intenta de nuevo.")
        return

    # Comando
    if text.startswith("/"):
        response = dispatch(text, user_id, username)
        if response:
            send_to_user(user_id, response)
        return

    # Texto libre → chat con el agente
    if not is_authorized_user(user_id):
        send_to_user(user_id, "⛔ No autorizado. Usa /start para autenticarte.")
        return

    # Indicador de escritura
    _api(token, "sendChatAction", chat_id=user_id, action="typing")

    from app.security.telegram.chat import chat
    reply = chat(user_id, text, username)
    if reply:
        send_to_user(user_id, reply)


def _handle_callback(token: str, cb: dict) -> None:
    """Maneja callback_query (botones inline)."""
    user = cb.get("from", {})
    user_id = user.get("id", 0)
    data = cb.get("data", "")
    msg_id = cb.get("message", {}).get("message_id")
    chat_id = cb.get("message", {}).get("chat", {}).get("id")

    # Responder al callback (quitar el spinner del botón)
    _api(token, "answerCallbackQuery", callback_query_id=cb["id"])

    from app.security.telegram.auth import is_authorized_user
    from app.security.telegram.notify import send_to_user
    if not is_authorized_user(user_id):
        return

    try:
        from app.comms.callbacks import handle_callback
        result = handle_callback(data, user_id)
        if result:
            reply_text = result.get("text", "")
            if reply_text:
                send_to_user(user_id, reply_text)
    except Exception as e:
        logger.error("callback error: %s", e)


def _poll_loop() -> None:
    global _running, _offset
    token = _token()
    if not token:
        logger.warning("TelegramBot: no token — bot desactivado")
        return

    logger.info("TelegramBot: iniciando long-polling")
    while _running:
        try:
            updates = _get_updates(token, _offset)
            for upd in updates:
                try:
                    _handle_update(token, upd)
                except Exception as e:
                    logger.error("update error: %s", e)
        except Exception as e:
            logger.error("poll error: %s", e)
            time.sleep(5)


def start() -> None:
    """Arranca el bot en un thread daemon (gateado por SECURITY_ENABLED)."""
    global _running, _thread
    if os.environ.get("SECURITY_ENABLED", "0") != "1":
        return
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_poll_loop, name="TelegramBot", daemon=True)
    _thread.start()
    logger.info("TelegramBot: thread iniciado")


def stop() -> None:
    global _running
    _running = False


def status() -> dict:
    return {
        "running": _running,
        "thread_alive": _thread is not None and _thread.is_alive(),
        "offset": _offset,
    }
