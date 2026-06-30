"""
Modo Claude: invoca el CLI de Claude Code (claude.exe) en headless con
--dangerously-skip-permissions y streamea la respuesta. Mantiene la conversación
por sesión web (--resume <session_id>), así cada instancia/persona tiene su hilo.

Esto da acceso DIRECTO a Claude Code desde la web (móvil incluido) con permisos
saltados: control total del PC. Solo para el dueño autenticado.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading

# web_session_id → claude_session_id (para --resume y mantener contexto)
_SESSIONS: dict[str, str] = {}
_LOCK = threading.Lock()

_BASE_CWD = os.environ.get("CLAUDE_MODE_CWD") or os.path.expanduser("~")


def _claude_bin() -> str | None:
    return (shutil.which("claude")
            or os.path.expandvars(r"%USERPROFILE%\.local\bin\claude.exe"))


def available() -> bool:
    b = _claude_bin()
    return bool(b and os.path.isfile(b))


def stream_claude(prompt: str, web_session: str = "", *,
                  emit_token=lambda s: None,
                  emit_status=lambda s: None,
                  should_stop=lambda: False) -> dict:
    """Ejecuta `claude -p` (skip permissions) y streamea el texto del asistente.
    Devuelve {ok, text, session_id|error}."""
    claude = _claude_bin()
    if not claude or not os.path.isfile(claude):
        return {"ok": False, "error": "claude.exe no encontrado en el PC"}

    cmd = [claude, "-p", prompt,
           "--dangerously-skip-permissions",
           "--output-format", "stream-json", "--verbose"]
    with _LOCK:
        csid = _SESSIONS.get(web_session) if web_session else None
    if csid:
        cmd += ["--resume", csid]

    emit_status("🤖 Claude Code está trabajando (permisos saltados)…")
    try:
        proc = subprocess.Popen(
            cmd, cwd=_BASE_CWD,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        return {"ok": False, "error": f"no se pudo lanzar claude: {e}"}

    full = []
    new_sid = None
    try:
        for line in proc.stdout:
            if should_stop():
                try:
                    proc.terminate()
                except Exception:
                    pass
                break
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except Exception:
                continue
            etype = evt.get("type")
            if etype == "assistant":
                for block in (evt.get("message", {}).get("content") or []):
                    if block.get("type") == "text" and block.get("text"):
                        emit_token(block["text"])
                        full.append(block["text"])
                    elif block.get("type") == "tool_use":
                        emit_status(f"🔧 {block.get('name', 'herramienta')}")
            elif etype == "result":
                new_sid = evt.get("session_id") or new_sid
                if evt.get("is_error"):
                    err = evt.get("result") or "error en Claude"
                    if not full:
                        return {"ok": False, "error": str(err)[:500]}
            elif etype == "system" and evt.get("session_id"):
                new_sid = evt["session_id"]
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    # si --resume falló (sesión vieja inválida), reintenta fresco una vez
    if not full and csid:
        with _LOCK:
            _SESSIONS.pop(web_session, None)
        return stream_claude(prompt, web_session, emit_token=emit_token,
                             emit_status=emit_status, should_stop=should_stop)

    if web_session and new_sid:
        with _LOCK:
            _SESSIONS[web_session] = new_sid
    return {"ok": True, "text": "".join(full), "session_id": new_sid}
