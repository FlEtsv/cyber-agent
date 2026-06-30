"""
B-07: Sanitizado HTML para Telegram.

Convierte Markdown a HTML de Telegram, quita bloques <think>...</think>,
recorta a 4096 chars y escapa caracteres especiales.
"""
from __future__ import annotations

import re


def strip_think(text: str) -> str:
    """Elimina bloques <think>…</think> del razonamiento interno."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()


def md_to_html(text: str) -> str:
    """Convierte Markdown básico a HTML de Telegram (negrita, cursiva, código)."""
    # Bloques de código (triple backtick) → <pre>
    text = re.sub(r"```(?:\w+)?\n?([\s\S]*?)```", lambda m: f"<pre>{_esc(m.group(1).strip())}</pre>", text)
    # Inline code → <code>
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{_esc(m.group(1))}</code>", text)
    # **bold**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # *italic* o _italic_
    text = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    # ### headers → <b>
    text = re.sub(r"^#{1,3} (.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    # --- separador → línea
    text = re.sub(r"^---+$", "─" * 20, text, flags=re.MULTILINE)
    return text


def sanitize(text: str, max_len: int = 4096) -> str:
    """Pipeline completo: strip_think → md_to_html → recortar."""
    text = strip_think(text)
    text = md_to_html(text)
    if len(text) > max_len:
        text = text[: max_len - 3] + "…"
    return text


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc(s: str) -> str:
    """Escapa para HTML de Telegram (usar en textos dinámicos no formateados)."""
    return _esc(str(s))
