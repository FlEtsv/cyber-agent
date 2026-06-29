"""
Adjuntos NO-imagen (scripts, código, docs, pdf, csv, json…) — fuente única.

Procesa los archivos que el usuario adjunta desde la web/PC:
  - Texto/código  → se inyecta el contenido en el prompt (recortado).
  - Binario (pdf/docx/xlsx/…) → se guarda y se extrae texto con `read_document`.

Además, cada adjunto se guarda en disco y se registra como archivo de la
conversación (WEBPROD-011), para poder accederlo después.
"""
from __future__ import annotations

import base64
import os
import re
import time

_BASE = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(_BASE, "web", "served", "uploads")
_MAX_FILES = 6
_MAX_TEXT = 20000


def _ensure() -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def _safe_name(name: str) -> str:
    name = os.path.basename(name or "").strip() or f"adjunto_{int(time.time())}"
    name = re.sub(r"[^A-Za-z0-9._\-]", "_", name)
    return name[:120]


def _clip(text: str) -> tuple[str, bool]:
    if len(text) > _MAX_TEXT:
        return text[:_MAX_TEXT] + "\n…[recortado]…", True
    return text, False


def _register(path: str, name: str, conversation_id, folder_id) -> str:
    """Guarda el adjunto como archivo de la conversación y devuelve su URL relativa."""
    url = f"/served/uploads/{os.path.basename(path)}"
    try:
        from app import database as _db
        _db.register_file(path, name=name, url=url,
                          folder_id=folder_id, conversation_id=conversation_id)
    except Exception:
        pass
    return url


def _one(att: dict, conversation_id, folder_id) -> str:
    name = _safe_name(att.get("name") or "adjunto")
    text = att.get("text")
    b64 = att.get("b64") or ""

    # 1) Texto/código directo desde el navegador.
    if isinstance(text, str) and text.strip():
        _ensure()
        path = os.path.join(UPLOAD_DIR, name)
        try:
            with open(path, "w", encoding="utf-8", errors="replace") as f:
                f.write(text)
            _register(path, name, conversation_id, folder_id)
        except Exception:
            pass
        body, _ = _clip(text)
        return f"\n\n[Archivo adjunto: {name}]\n```\n{body}\n```"

    # 2) Binario (pdf/docx/xlsx/…): guardar y extraer con read_document.
    if b64:
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        _ensure()
        path = os.path.join(UPLOAD_DIR, name)
        try:
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
        except Exception as e:
            return f"\n\n[Archivo adjunto: {name} — error al guardar: {e}]"
        _register(path, name, conversation_id, folder_id)
        try:
            from app.tools_ext import read_document
            res = read_document(path)
            if res.get("ok"):
                body, _ = _clip(res.get("text", ""))
                return f"\n\n[Archivo adjunto: {name} ({res.get('type', '?')})]\n```\n{body}\n```"
            return f"\n\n[Archivo adjunto: {name} — no se pudo leer: {res.get('error')}]"
        except Exception as e:
            return f"\n\n[Archivo adjunto: {name} — error de lectura: {e}]"

    return ""


def process_attachments(files: list[dict], conversation_id=None, folder_id=None) -> str:
    """Convierte una lista de adjuntos en un bloque de texto para inyectar en el prompt."""
    parts: list[str] = []
    for att in (files or [])[:_MAX_FILES]:
        if isinstance(att, dict):
            try:
                parts.append(_one(att, conversation_id, folder_id))
            except Exception as e:
                parts.append(f"\n\n[Archivo adjunto — error: {e}]")
    return "".join(p for p in parts if p)
