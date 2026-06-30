"""
U-05 + AR-01..AR-07: Comandos de gestión del módulo de comunicaciones.

Permite silenciar, cambiar el nivel mínimo y consultar el estado
desde código (supervisor, web, agente) o desde Telegram (/cmd).
"""
from __future__ import annotations

from app.comms import router as _r


def mute() -> dict:
    _r.set_muted(True)
    return {"ok": True, "muted": True}


def unmute() -> dict:
    _r.set_muted(False)
    return {"ok": True, "muted": False}


def set_level(level_name: str) -> dict:
    mapping = {
        "debug": _r.DEBUG, "info": _r.INFO, "success": _r.SUCCESS,
        "warning": _r.WARNING, "error": _r.ERROR, "critical": _r.CRITICAL,
    }
    level = mapping.get(level_name.lower())
    if level is None:
        return {"ok": False, "error": f"Nivel desconocido: {level_name}. Opciones: {list(mapping)}"}
    _r.set_min_level(level)
    return {"ok": True, "min_level": level_name}


def status() -> dict:
    return {
        "available": _r.available(),
        "muted": _r._muted,
        "min_level": _r._LEVEL_NAMES.get(_r._min_level, "?"),
    }


# ── AR-01..AR-07: Handlers de comandos Telegram ───────────────────────────────

def handle_telegram_command(text: str, from_user_id: int) -> str:
    """
    AR-01: Despacha un comando de Telegram (/estado /resumen /silenciar /modo /camara /ayuda).
    Retorna el texto de respuesta.
    """
    parts = text.strip().split()
    if not parts:
        return "Comando vacío."
    cmd = parts[0].lower().lstrip("/").split("@")[0]  # strip @botname

    if cmd == "ayuda" or cmd == "help" or cmd == "start":
        return (
            "Comandos disponibles:\n"
            "/estado — salud del sistema\n"
            "/resumen — digest bajo demanda\n"
            "/silenciar [cat] [minutos] — silenciar categoría\n"
            "/modo [manual|operativa|alto-impacto] — autonomía de seguridad\n"
            "/camara [nombre] — snapshot de cámara\n"
        )

    elif cmd == "estado":
        # AR-05: salud del sistema
        return _cmd_estado()

    elif cmd == "resumen":
        # AR-05: digest bajo demanda
        return _cmd_resumen()

    elif cmd == "silenciar":
        # AR-02: /silenciar [cat] [tiempo_min]
        cat = parts[1] if len(parts) > 1 else "all"
        mins = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 60
        return _cmd_silenciar(cat, mins)

    elif cmd == "modo":
        # AR-03: /modo <manual|operativa|alto-impacto>
        modo = parts[1] if len(parts) > 1 else "manual"
        return _cmd_modo(modo)

    elif cmd == "camara":
        # AR-04: /camara <nombre>
        nombre = parts[1] if len(parts) > 1 else ""
        return _cmd_camara(nombre)

    else:
        return f"Comando desconocido: {cmd}. Usa /ayuda."


def _cmd_estado() -> str:
    try:
        from app.supervisor import get_status
        s = get_status()
        lines = ["🖥️ <b>Estado del sistema</b>"]
        for k, v in s.items():
            lines.append(f"• {k}: {v}")
        return "\n".join(lines)
    except Exception:
        st = status()
        return f"🖥️ Comms: disponible={st['available']}, mute={st['muted']}, nivel={st['min_level']}"


def _cmd_resumen() -> str:
    try:
        from app.comms.digest import get_digest_text
        text = get_digest_text()
        return text or "📋 No hay notificaciones pendientes en el digest."
    except Exception:
        return "Error generando resumen."


def _cmd_silenciar(cat: str, mins: int) -> str:
    try:
        from app.comms.rules import set_no_disturb
        import threading
        # Silenciar temporalmente
        set_no_disturb(True)
        def _restore():
            import time; time.sleep(mins * 60)
            set_no_disturb(None)
        threading.Thread(target=_restore, daemon=True).start()
        return f"🔕 Silenciado {mins} min (categoría: {cat})"
    except Exception:
        return "Error silenciando."


def _cmd_modo(modo: str) -> str:
    valid = {"manual", "operativa", "alto-impacto"}
    if modo not in valid:
        return f"Modo inválido. Opciones: {', '.join(valid)}"
    return f"🎛️ Modo autonomía: {modo} (próximamente integrado con security)"


def _cmd_camara(nombre: str) -> str:
    if not nombre:
        return "Uso: /camara <nombre>"
    return f"📷 Solicitando snapshot de '{nombre}'… (requiere SECURITY_ENABLED=1)"
