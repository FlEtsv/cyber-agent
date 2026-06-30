"""
B-08: Notificaciones a chat principal + viewers adicionales.

Envía a:
  1. Chat principal (SEC_TELEGRAM_CHAT_ID)
  2. Todos los viewers activos en viewer_store

Incluye soporte de topics (forum threads) y teclados inline.
"""
from __future__ import annotations

import httpx

from app.security.telegram.format import sanitize, esc


def _cfg() -> tuple[str | None, str | None]:
    try:
        from app.secrets_vault import get_secret
        token = get_secret("SEC_TELEGRAM_BOT_TOKEN")
        chat_id = get_secret("SEC_TELEGRAM_CHAT_ID")
        return token, chat_id
    except Exception:
        return None, None


def _send_raw(
    token: str,
    chat_id: str | int,
    text: str,
    reply_markup: dict | None = None,
    disable_notification: bool = False,
    thread_id: int | None = None,
) -> dict:
    payload: dict = {
        "chat_id": chat_id,
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": disable_notification,
    }
    if reply_markup:
        import json
        payload["reply_markup"] = json.dumps(reply_markup)
    if thread_id:
        payload["message_thread_id"] = thread_id
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=15,
        )
        data = r.json()
        return {"ok": data.get("ok", False), "message_id": data.get("result", {}).get("message_id")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_photo(token: str, chat_id: str | int, image_b64: str, caption: str = "") -> dict:
    """Envía foto desde base64."""
    import base64
    try:
        img_bytes = base64.b64decode(image_b64)
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption[:1024], "parse_mode": "HTML"},
            files={"photo": ("snapshot.jpg", img_bytes, "image/jpeg")},
            timeout=30,
        )
        data = r.json()
        return {"ok": data.get("ok", False)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def broadcast(
    title: str,
    body: str = "",
    emoji: str = "🔔",
    keyboard: dict | None = None,
    silent: bool = False,
    image_b64: str | None = None,
) -> list[dict]:
    """
    Envía a chat principal + todos los viewers activos.
    Retorna lista de resultados por destino.
    """
    token, main_chat = _cfg()
    if not token:
        return [{"ok": False, "error": "Telegram no configurado"}]

    text = f"{emoji} <b>{esc(title)}</b>"
    if body:
        text += f"\n{sanitize(body)}"

    results = []

    # Chat principal
    if main_chat:
        if image_b64:
            results.append(send_photo(token, main_chat, image_b64, caption=f"{emoji} {title}"))
        else:
            results.append(_send_raw(token, main_chat, text, keyboard, silent))

    # Viewers adicionales (excepto el chat principal)
    try:
        from app.security.telegram.viewers import get_viewers
        for v in get_viewers():
            uid = v["user_id"]
            if str(uid) == str(main_chat):
                continue
            if image_b64:
                results.append(send_photo(token, uid, image_b64, caption=f"{emoji} {title}"))
            else:
                results.append(_send_raw(token, uid, text, keyboard, silent))
    except Exception:
        pass

    return results


def send_to_user(
    user_id: int,
    text: str,
    keyboard: dict | None = None,
) -> dict:
    """Envía directamente a un user_id (respuesta a comando)."""
    token, _ = _cfg()
    if not token:
        return {"ok": False, "error": "no token"}
    return _send_raw(token, user_id, sanitize(text), keyboard)


def edit_message(message_id: int, chat_id: str | int, new_text: str) -> dict:
    """Edita un mensaje ya enviado (AO-05: analizando→resuelto)."""
    token, main_chat = _cfg()
    if not token:
        return {"ok": False, "error": "no token"}
    cid = chat_id or main_chat
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/editMessageText",
            json={
                "chat_id": cid,
                "message_id": message_id,
                "text": new_text[:4096],
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        return {"ok": r.json().get("ok", False)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
