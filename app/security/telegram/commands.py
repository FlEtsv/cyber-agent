"""
B-02 + B-09: Comandos del bot de Telegram.

/start /help /status /pending /autonomia /addviewer /snapcam /resumen /limpiar
"""
from __future__ import annotations

from app.security.telegram.auth import is_admin_user, is_authorized_user, challenge
from app.security.telegram.notify import send_to_user


def dispatch(text: str, user_id: int, username: str = "") -> str | None:
    """
    Despacha un comando de texto. Retorna la respuesta o None si no es comando.
    """
    text = text.strip()
    if not text.startswith("/"):
        return None

    parts = text.split()
    cmd = parts[0].lower().lstrip("/").split("@")[0]

    # Sin autenticación
    if cmd == "start":
        return _cmd_start(user_id, username)
    if cmd in ("help", "ayuda"):
        return _cmd_help(user_id)

    # Con autenticación
    if not is_authorized_user(user_id):
        if _maybe_totp(text, user_id, username):
            return "✅ Autenticado correctamente. Bienvenido."
        return "⛔ No autorizado. Usa /start para autenticarte."

    if cmd == "status" or cmd == "estado":
        return _cmd_status()
    if cmd == "pending":
        return _cmd_pending()
    if cmd == "resumen":
        return _cmd_resumen()
    if cmd == "limpiar":
        from app.security.telegram.chat import clear_history
        clear_history(user_id)
        return "🗑️ Historial de chat limpiado."
    if cmd == "autonomia" or cmd == "autonomy":
        modo = parts[1] if len(parts) > 1 else ""
        return _cmd_autonomia(modo, user_id)
    if cmd == "silenciar":
        cat = parts[1] if len(parts) > 1 else "all"
        mins = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 60
        return _cmd_silenciar(cat, mins)
    if cmd == "snapcam" or cmd == "camara":
        cam = parts[1] if len(parts) > 1 else ""
        return _cmd_snapcam(cam, user_id)
    if cmd == "addviewer" and is_admin_user(user_id):
        uid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        return _cmd_addviewer(uid)
    if cmd == "delviewer" and is_admin_user(user_id):
        uid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        return _cmd_delviewer(uid)
    if cmd == "viewers" and is_admin_user(user_id):
        return _cmd_viewers()

    return f"Comando desconocido: /{cmd}\nUsa /help para ver los disponibles."


def _maybe_totp(text: str, user_id: int, username: str) -> bool:
    """Intenta resolver un challenge TOTP si el texto parece un código de 6 dígitos."""
    stripped = text.strip()
    if stripped.isdigit() and len(stripped) == 6:
        from app.security.telegram.auth import resolve_challenge, is_challenge_pending
        if is_challenge_pending(user_id):
            return resolve_challenge(user_id, stripped, username)
    return False


def _cmd_start(user_id: int, username: str) -> str:
    if is_authorized_user(user_id):
        return (
            "👋 <b>CyberAgent</b> activo.\n"
            "Usa /help para ver los comandos disponibles.\n"
            "Escribe cualquier mensaje para chatear con el agente."
        )
    # Lanzar challenge TOTP
    from app.security.telegram.auth import challenge
    has_totp = challenge(user_id)
    if has_totp:
        return (
            "🔐 <b>Autenticación requerida</b>\n"
            "Abre tu app de autenticación y envía el código de 6 dígitos."
        )
    return (
        "⛔ Acceso no configurado. El administrador debe añadirte "
        "con /addviewer o configurar el TOTP."
    )


def _cmd_help(user_id: int) -> str:
    base = (
        "📋 <b>Comandos CyberAgent</b>\n\n"
        "/start — iniciar / autenticar\n"
        "/help — esta ayuda\n"
    )
    if not is_authorized_user(user_id):
        return base
    base += (
        "/estado — salud del sistema\n"
        "/pending — aprobaciones pendientes\n"
        "/resumen — digest de notificaciones\n"
        "/autonomia [modo] — ver/cambiar modo de autonomía\n"
        "/silenciar [cat] [mins] — silenciar notificaciones\n"
        "/snapcam [nombre] — snapshot de cámara\n"
        "/limpiar — borrar historial de chat\n"
    )
    if is_admin_user(user_id):
        base += (
            "\n<b>Admin:</b>\n"
            "/addviewer <user_id> — añadir viewer\n"
            "/delviewer <user_id> — eliminar viewer\n"
            "/viewers — listar viewers\n"
        )
    return base


def _cmd_status() -> str:
    lines = ["🖥️ <b>Estado del sistema</b>\n"]
    try:
        from app.supervisor import get_status
        s = get_status()
        for k, v in s.items():
            lines.append(f"• {k}: {v}")
    except Exception as e:
        lines.append(f"• supervisor: error ({e})")
    try:
        from app.comms.commands import status as comms_status
        s = comms_status()
        lines.append(f"• comms: mute={s['muted']}, nivel={s['min_level']}")
    except Exception:
        pass
    try:
        from app.security.autonomy import get_mode
        lines.append(f"• autonomía: {get_mode()}")
    except Exception:
        pass
    return "\n".join(lines)


def _cmd_pending() -> str:
    try:
        from app.security.actions import pending_list
        items = pending_list()
        if not items:
            return "✅ No hay acciones pendientes de aprobación."
        lines = ["⏳ <b>Acciones pendientes:</b>\n"]
        for it in items[:10]:
            lines.append(f"• [{it.get('run_id','')}] {it.get('tool','')} — {it.get('preview','')[:60]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error obteniendo pendientes: {e}"


def _cmd_resumen() -> str:
    try:
        from app.comms.digest import get_digest_text
        t = get_digest_text()
        return t or "📋 No hay notificaciones en el digest."
    except Exception:
        return "Error generando resumen."


def _cmd_autonomia(modo: str, user_id: int) -> str:
    try:
        from app.security.autonomy import get_mode, set_mode
        if not modo:
            return f"🎛️ Modo actual: <b>{get_mode()}</b>\nOpciones: manual | operativa | alto-impacto"
        if not is_admin_user(user_id):
            return "⛔ Solo el admin puede cambiar el modo de autonomía."
        result = set_mode(modo)
        if result.get("ok"):
            return f"🎛️ Modo autonomía cambiado a: <b>{modo}</b>"
        return f"Error: {result.get('error')}"
    except Exception as e:
        return f"Error: {e}"


def _cmd_silenciar(cat: str, mins: int) -> str:
    try:
        from app.comms.rules import set_no_disturb
        import threading, time
        set_no_disturb(True)
        def _restore():
            time.sleep(mins * 60)
            set_no_disturb(None)
        threading.Thread(target=_restore, daemon=True).start()
        return f"🔕 Silenciado {mins} min (cat: {cat})"
    except Exception as e:
        return f"Error: {e}"


def _cmd_snapcam(cam_name: str, user_id: int) -> str:
    if not cam_name:
        return "Uso: /snapcam <nombre_camara>"
    try:
        from app.security.camera import snapshot_by_name
        result = snapshot_by_name(cam_name)
        if result.get("ok") and result.get("image_b64"):
            from app.security.telegram.notify import send_photo
            from app.secrets_vault import get_secret
            token = get_secret("SEC_TELEGRAM_BOT_TOKEN")
            if token:
                send_photo(token, user_id, result["image_b64"], f"📷 {cam_name}")
            return ""  # foto enviada aparte
        return f"Error capturando snapshot: {result.get('error', 'sin imagen')}"
    except Exception as e:
        return f"Error: {e}"


def _cmd_addviewer(uid: int | None) -> str:
    if not uid:
        return "Uso: /addviewer <user_id>"
    from app.security.telegram.viewers import add_viewer
    add_viewer(uid, role="viewer")
    return f"✅ Viewer {uid} añadido."


def _cmd_delviewer(uid: int | None) -> str:
    if not uid:
        return "Uso: /delviewer <user_id>"
    from app.security.telegram.viewers import remove_viewer
    remove_viewer(uid)
    return f"✅ Viewer {uid} eliminado."


def _cmd_viewers() -> str:
    from app.security.telegram.viewers import list_all
    vs = list_all()
    if not vs:
        return "No hay viewers registrados."
    lines = ["👥 <b>Viewers:</b>"]
    for v in vs:
        lines.append(f"• {v['user_id']} ({v['username']}) — {v['role']}")
    return "\n".join(lines)
