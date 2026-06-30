"""
Notificador de Telegram de CyberAgent (ACTIVO).

Canal de notificación saliente: CyberAgent avisa por Telegram (tarea terminada,
aprobación pendiente, alerta de seguridad…). Usa el MISMO bot de APiComuni
(SEC_TELEGRAM_BOT_TOKEN / SEC_TELEGRAM_CHAT_ID en el gestor de secretos) — solo
cambia el propósito. Solo API HTTP de Telegram (sin dependencia pesada).
"""
from __future__ import annotations

import os

import httpx


def _cfg() -> tuple[str | None, str | None]:
    """(token, chat_id) desde el vault o, en su defecto, el entorno."""
    try:
        from app.secrets_vault import get_secret
        token = get_secret("SEC_TELEGRAM_BOT_TOKEN") or os.environ.get("SEC_TELEGRAM_BOT_TOKEN")
        chat = get_secret("SEC_TELEGRAM_CHAT_ID") or os.environ.get("SEC_TELEGRAM_CHAT_ID")
    except Exception:
        token = os.environ.get("SEC_TELEGRAM_BOT_TOKEN")
        chat = os.environ.get("SEC_TELEGRAM_CHAT_ID")
    return (token or None), (chat or None)


def available() -> bool:
    t, c = _cfg()
    return bool(t and c)


def send(text: str, chat_id: str | None = None, parse_mode: str = "HTML") -> dict:
    """AQ-03: Envía un mensaje por Telegram con rate-limiting integrado."""
    token, default_chat = _cfg()
    chat = chat_id or default_chat
    if not token or not chat:
        return {"ok": False, "error": "Telegram no configurado (faltan token/chat_id en el vault)"}

    # AQ-03: Respetar límites de Telegram con rate limiter
    try:
        from app.comms.rate_limiter import get_limiter
        limiter = get_limiter(chat)
        limiter.acquire()
    except Exception:
        pass

    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text[:4096],
                  "parse_mode": parse_mode, "disable_web_page_preview": True},
            timeout=15,
        )
        if r.status_code == 429:
            retry_after = r.json().get("parameters", {}).get("retry_after", 5)
            import time
            time.sleep(retry_after)
            r = httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": text[:4096],
                      "parse_mode": parse_mode, "disable_web_page_preview": True},
                timeout=15,
            )
        ok = r.status_code == 200 and r.json().get("ok", False)
        return {"ok": ok, "status": r.status_code,
                "error": None if ok else r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def notify(title: str, body: str = "", emoji: str = "🔔") -> dict:
    """Notificación con formato: título en negrita + cuerpo."""
    text = f"{emoji} <b>{_esc(title)}</b>"
    if body:
        text += f"\n{_esc(body)}"
    return send(text)


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
