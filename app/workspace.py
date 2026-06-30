"""
Dispatch de acciones del workspace (carpetas, conversaciones, archivos, Google).

Fuente ÚNICA usada por el puente del relay (`relay_connector`) y por el WebSocket
local (`server.py`), para que el workspace funcione igual desde el móvil y desde
localhost. SQLite del PC es la fuente de la verdad.

`handle_sync` resuelve TODO menos `google_connect` (que abre el navegador y bloquea;
lo gestiona cada llamador en un hilo).
"""
from __future__ import annotations


def handle_sync(action: str, msg: dict) -> dict:
    """Ejecuta una acción workspace sin bloquear. Devuelve el dict de resultado."""
    from app import database as db
    try:
        if action == "get":
            return {"folders": db.get_folders(), "conversations": db.get_conversations()}
        if action == "files_get":
            return {"files": db.get_files(
                conversation_id=msg.get("conversation_id", "__all__"),
                favorites_only=bool(msg.get("favorites_only", False)))}
        # G-04: gestor de secretos por el relay (móvil). reveal exige TOTP.
        if action == "vault_list":
            from app.secrets_vault import list_secrets_masked
            return {"secrets": [{**s, "key": s.get("name")} for s in list_secrets_masked()]}
        if action == "vault_reveal":
            from app.secrets_vault import _verify_totp, get_secret
            key = (msg.get("key") or "").strip()
            code = str(msg.get("totp") or "").strip()
            if not key:
                return {"ok": False, "error": "key requerida"}
            if not _verify_totp(code):
                return {"ok": False, "error": "Código TOTP inválido"}
            val = get_secret(key)
            return {"ok": val is not None, "key": key, "value": val}
        if action == "vault_set":
            from app.secrets_vault import set_secret
            key = (msg.get("key") or "").strip()
            if not key:
                return {"ok": False, "error": "key requerida"}
            set_secret(key, msg.get("value") or "")
            return {"ok": True}
        if action == "deployments":
            from app.deployer import registered_deployments
            return registered_deployments()
        if action == "file_favorite":
            db.set_file_favorite(msg["file_id"], bool(msg.get("favorite", True)))
            return {"ok": True}
        if action == "file_delete":
            db.delete_file(msg["file_id"])
            return {"ok": True}
        if action == "conv_files_cleanup":
            db.cleanup_conversation_files(msg.get("conversation_id"))
            return {"ok": True}
        if action == "folder_create":
            return {"id": db.create_folder(
                msg.get("name", ""), msg.get("parent_id"), msg.get("color"),
                msg.get("context", ""), msg.get("default_model"))}
        if action == "folder_update":
            db.update_folder(msg["id"], **{k: msg[k] for k in
                ("name", "parent_id", "color", "context", "default_model", "position")
                if k in msg})
            return {"ok": True}
        if action == "folder_delete":
            db.delete_folder(msg["id"])
            return {"ok": True}
        if action == "conv_move":
            db.move_conversation(msg["conv_id"], msg.get("folder_id"))
            return {"ok": True}
        if action == "conv_color":
            db.set_conversation_color(msg["conv_id"], msg.get("color"))
            return {"ok": True}
        if action == "google_status":
            from app import google_suite as g
            return g.google_status()
        if action == "google_disconnect":
            from app import google_suite as g
            return g.google_disconnect()
        return {"error": f"acción desconocida: {action}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
