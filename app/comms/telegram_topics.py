"""
AN-01 + AN-02 + AN-05: Supergrupo FORO de Telegram con Topics.

Detecta si el chat configurado soporta forum topics; si sí, envía a hilos
diferenciados por categoría. Si no, fallback a prefijo de severidad (AN-03).

Temas por defecto (AN-05):
  - Urgente     → urgencia inmediata, sonido
  - Seguridad   → alertas de cámara/intrusión
  - Notificaciones → agente: tarea hecha, aprobaciones
  - Gatos       → actividad/anomalías de mascotas
  - Periódico   → resúmenes, digests
  - Sistema     → salud del sistema, errores
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import NamedTuple

_TOPICS_FILE = Path(__file__).parent.parent.parent / "data" / "telegram_topics.json"
_lock = threading.Lock()

TOPIC_NAMES = [
    "Urgente",
    "Seguridad",
    "Notificaciones",
    "Gatos",
    "Periódico",
    "Sistema",
]

CATEGORY_TO_TOPIC: dict[str, str] = {
    "critical": "Urgente",
    "security": "Seguridad",
    "threat": "Seguridad",
    "agent": "Notificaciones",
    "approval": "Notificaciones",
    "cats": "Gatos",
    "pet": "Gatos",
    "periodic": "Periódico",
    "digest": "Periódico",
    "system": "Sistema",
    "error": "Sistema",
}

SEVERITY_PREFIX: dict[str, str] = {
    "critical": "🔴",
    "security": "🛡️",
    "threat": "🛡️",
    "agent": "🔔",
    "approval": "🔔",
    "cats": "🐱",
    "pet": "🐱",
    "periodic": "📊",
    "digest": "📊",
    "system": "⚙️",
    "error": "⚠️",
}


def _load() -> dict:
    if _TOPICS_FILE.exists():
        try:
            return json.loads(_TOPICS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict):
    _TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TOPICS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_thread_id(topic_name: str) -> int | None:
    """Devuelve el message_thread_id de un tema por su nombre, o None si no existe."""
    with _lock:
        data = _load()
    return data.get("topics", {}).get(topic_name)


def set_thread_id(topic_name: str, thread_id: int):
    """Guarda el message_thread_id de un tema."""
    with _lock:
        data = _load()
        data.setdefault("topics", {})[topic_name] = thread_id
        _save(data)


def has_forum_support() -> bool:
    """¿Tenemos al menos un topic guardado → se usa foro?"""
    with _lock:
        data = _load()
    return bool(data.get("topics"))


def setup_topics(bot_token: str, chat_id: str | int) -> dict:
    """
    AN-01 + AN-05: Intenta crear los temas por defecto en el supergrupo.
    Si ya existen (guardados en JSON), los devuelve. Si no, los crea.

    NOTA: Requiere que el chat sea un supergrupo foro.
    Usa la API de Telegram directamente (requests).
    """
    try:
        import httpx
    except ImportError:
        return {"ok": False, "error": "httpx not available"}

    base_url = f"https://api.telegram.org/bot{bot_token}"
    created: dict[str, int] = {}
    existing = _load().get("topics", {})

    for topic in TOPIC_NAMES:
        if topic in existing:
            created[topic] = existing[topic]
            continue
        try:
            r = httpx.post(
                f"{base_url}/createForumTopic",
                json={"chat_id": chat_id, "name": topic},
                timeout=10,
            )
            if r.status_code == 200 and r.json().get("ok"):
                thread_id = r.json()["result"]["message_thread_id"]
                set_thread_id(topic, thread_id)
                created[topic] = thread_id
        except Exception:
            pass

    return {"ok": True, "topics": created}


def resolve_thread(category: str) -> int | None:
    """
    AN-02: Devuelve el message_thread_id para la categoría dada.
    None si no hay topics configurados (AN-03 fallback).
    """
    topic_name = CATEGORY_TO_TOPIC.get(category)
    if not topic_name:
        return None
    return get_thread_id(topic_name)


def format_with_prefix(category: str, title: str, body: str) -> str:
    """
    AN-03: Fallback sin Topics — añade prefijo de severidad al mensaje.
    """
    prefix = SEVERITY_PREFIX.get(category, "📌")
    return f"{prefix} <b>{title}</b>\n{body}"


def send_to_topic(
    bot_token: str,
    chat_id: str | int,
    category: str,
    title: str,
    body: str,
    disable_notification: bool = False,
) -> bool:
    """
    AN-02: Envía un mensaje al topic correcto (o fallback sin topic).
    Retorna True si se envió correctamente.
    """
    try:
        import httpx
    except ImportError:
        return False

    thread_id = resolve_thread(category)
    text = f"<b>{title}</b>\n{body}"

    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": disable_notification,
    }
    if thread_id is not None:
        payload["message_thread_id"] = thread_id

    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=10,
        )
        return r.status_code == 200 and r.json().get("ok", False)
    except Exception:
        return False
