"""
AQ-03: Rate-limit de Telegram + cola con reintento exponencial.

Telegram impone:
  - 30 mensajes/segundo global
  - 1 mensaje/segundo por chat
  - 20 mensajes/minuto por grupo

Este módulo:
  1. Aplica un rate-limiter de token-bucket (1 msg/s por chat)
  2. Cola los mensajes que exceden el límite
  3. Reintenta con backoff exponencial en caso de 429 (Too Many Requests)
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# Límites conservadores
_MIN_INTERVAL = 1.1       # segundos entre mensajes al mismo chat
_GLOBAL_RPS = 25          # mensajes/segundo global (margen de seguridad)
_MAX_RETRIES = 4
_BASE_BACKOFF = 2.0       # segundos base para backoff exponencial


@dataclass
class _QueuedMsg:
    token: str
    chat_id: str | int
    payload: dict
    retries: int = 0
    callback: object = None  # callable(dict) cuando se envía


_queue: queue.Queue = queue.Queue(maxsize=500)
_last_sent: dict[str | int, float] = {}  # chat_id → timestamp
_global_last: float = 0.0
_lock = threading.Lock()
_worker_started = False


def _can_send(chat_id: str | int) -> bool:
    now = time.time()
    with _lock:
        last_chat = _last_sent.get(chat_id, 0)
        last_global = _global_last
    return (now - last_chat >= _MIN_INTERVAL) and (now - last_global >= 1.0 / _GLOBAL_RPS)


def _mark_sent(chat_id: str | int) -> None:
    now = time.time()
    with _lock:
        global _global_last
        _last_sent[chat_id] = now
        _global_last = now


def _send_now(msg: _QueuedMsg) -> dict:
    """Intenta enviar inmediatamente vía HTTP."""
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{msg.token}/sendMessage",
            json={**msg.payload, "chat_id": msg.chat_id},
            timeout=15,
        )
        data = r.json()
        if r.status_code == 429:
            retry_after = data.get("parameters", {}).get("retry_after", _BASE_BACKOFF)
            return {"ok": False, "retry_after": retry_after, "status": 429}
        return {"ok": data.get("ok", False), "status": r.status_code,
                "message_id": data.get("result", {}).get("message_id")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _worker() -> None:
    """Thread daemon que procesa la cola con rate-limit."""
    while True:
        try:
            msg: _QueuedMsg = _queue.get(timeout=5)
        except queue.Empty:
            continue

        # Esperar si el chat tiene rate-limit activo
        for _ in range(20):
            if _can_send(msg.chat_id):
                break
            time.sleep(0.1)

        result = _send_now(msg)
        _mark_sent(msg.chat_id)

        if not result.get("ok"):
            retry_after = result.get("retry_after", 0)
            if retry_after > 0 and msg.retries < _MAX_RETRIES:
                # Reencolar con backoff
                backoff = retry_after + _BASE_BACKOFF * (2 ** msg.retries)
                logger.warning("rate_limiter: 429 — reintentando en %.1fs (intento %d)", backoff, msg.retries + 1)
                time.sleep(backoff)
                msg.retries += 1
                try:
                    _queue.put_nowait(msg)
                except queue.Full:
                    logger.error("rate_limiter: cola llena, mensaje descartado")
            else:
                logger.error("rate_limiter: mensaje descartado tras %d reintentos", msg.retries)

        if msg.callback:
            try:
                msg.callback(result)
            except Exception:
                pass

        _queue.task_done()


def _ensure_worker() -> None:
    global _worker_started
    if not _worker_started:
        _worker_started = True
        threading.Thread(target=_worker, name="TelegramRateLimiter", daemon=True).start()


def enqueue(
    token: str,
    chat_id: str | int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: dict | None = None,
    disable_notification: bool = False,
    callback=None,
) -> bool:
    """
    AQ-03: Encola un mensaje respetando el rate-limit de Telegram.

    Retorna True si se añadió a la cola, False si la cola está llena.
    """
    _ensure_worker()

    import json as _json
    payload: dict = {
        "text": text[:4096],
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
        "disable_notification": disable_notification,
    }
    if reply_markup:
        payload["reply_markup"] = _json.dumps(reply_markup)

    msg = _QueuedMsg(token=token, chat_id=chat_id, payload=payload, callback=callback)
    try:
        _queue.put_nowait(msg)
        return True
    except queue.Full:
        logger.error("rate_limiter: cola llena al encolar mensaje a %s", chat_id)
        return False


def queue_size() -> int:
    return _queue.qsize()


class _SimpleRateLimiter:
    """Token-bucket simple para acquire() sincrónico en notify.py."""
    def __init__(self, chat_id):
        self._chat_id = chat_id
        self._lock = threading.Lock()

    def acquire(self):
        while not _can_send(self._chat_id):
            time.sleep(0.1)
        _mark_sent(self._chat_id)


_limiters: dict[str, _SimpleRateLimiter] = {}
_limiter_lock = threading.Lock()


def get_limiter(chat_id: str | int) -> _SimpleRateLimiter:
    """Obtener (o crear) un rate-limiter para un chat específico."""
    key = str(chat_id)
    with _limiter_lock:
        if key not in _limiters:
            _limiters[key] = _SimpleRateLimiter(chat_id)
        return _limiters[key]
