from __future__ import annotations

import hashlib
import json
from typing import Iterable

RECENT_MESSAGES = 18
SUMMARY_MAX_CHARS = 6000
MESSAGE_SNIPPET_CHARS = 700
TOOL_PREVIEW_CHARS = 1200


def _shorten(text: str, max_chars: int) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 80].rstrip() + f"\n[... {len(text) - max_chars} caracteres omitidos ...]"


def _strip_status_lines(text: str) -> str:
    return "\n".join(
        line for line in (text or "").splitlines()
        if not line.strip().startswith("[estado]")
    ).strip()


def _message_line(message: dict) -> str:
    role = message.get("role", "?")
    content = " ".join(_strip_status_lines(message.get("content") or "").split())
    return f"- {role}: {_shorten(content, MESSAGE_SNIPPET_CHARS)}"


def summarize_messages(messages: Iterable[dict], max_chars: int = SUMMARY_MAX_CHARS) -> str:
    msgs = list(messages)
    lines: list[str] = []
    first_user: str | None = None
    for message in msgs:
        if message.get("role") not in ("user", "assistant"):
            continue
        content = _strip_status_lines(message.get("content") or "")
        if not content:
            continue
        if first_user is None and message.get("role") == "user":
            first_user = _shorten(" ".join(content.split()), 600)
        lines.append(_message_line(message))

    if not lines:
        return ""

    head = ""
    if first_user:
        # El objetivo original SIEMPRE se preserva, aunque caiga fuera de los últimos 40.
        head = f"OBJETIVO ORIGINAL DEL USUARIO: {first_user}\n\n"
    summary = "Resumen acumulado de la conversacion anterior:\n" + head + "\n".join(lines[-40:])
    return _shorten(summary, max_chars)


def refresh_conversation_memory(conversation_id: int, keep_recent: int = RECENT_MESSAGES) -> str:
    from app import database as db

    messages = db.get_messages(conversation_id)
    older = messages[:-keep_recent] if len(messages) > keep_recent else []
    summary = summarize_messages(older)
    db.save_memory_summary(conversation_id, summary)
    return summary


def get_conversation_memory(conversation_id: int | None) -> str:
    if not conversation_id:
        return ""
    try:
        from app import database as db

        return db.get_memory_summary(conversation_id)
    except Exception:
        return ""


def compact_tool_result(message: dict) -> dict:
    content = message.get("content") or ""
    if len(content) <= TOOL_PREVIEW_CHARS:
        return dict(message)

    digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()[:12]
    preview = _shorten(content, TOOL_PREVIEW_CHARS)
    compact = dict(message)
    compact["content"] = json.dumps(
        {
            "result_ref": digest,
            "note": "Resultado de herramienta compactado; usa el panel/log si necesitas el texto completo.",
            "preview": preview,
        },
        ensure_ascii=False,
    )
    return compact


def build_layered_history(
    system_prompt: str,
    messages: list[dict],
    conversation_id: int | None = None,
    keep_recent: int = RECENT_MESSAGES,
) -> list[dict]:
    older = messages[:-keep_recent] if len(messages) > keep_recent else []
    recent = messages[-keep_recent:] if keep_recent > 0 else messages

    memory = get_conversation_memory(conversation_id)
    if not memory and older:
        memory = summarize_messages(older)

    sys_content = system_prompt
    if memory:
        sys_content += "\n\n## MEMORIA DE LA CONVERSACION\n" + _shorten(memory, SUMMARY_MAX_CHARS)
    history = [{"role": "system", "content": sys_content}]

    for message in recent:
        if message.get("role") == "tool":
            history.append(compact_tool_result(message))
        else:
            msg = dict(message)
            if msg.get("role") == "assistant":
                msg["content"] = _strip_status_lines(msg.get("content") or "")
            history.append(msg)
    return history
