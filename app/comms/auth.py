"""
AS-02: Auth del módulo de comunicaciones.

Solo el admin puede ejecutar acciones; viewers solo ven.
Reutiliza TOTP del vault para validación de admin.
"""
from __future__ import annotations

import logging
import threading
from enum import Enum

logger = logging.getLogger(__name__)

_lock = threading.Lock()


class CommsRole(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"
    BLOCKED = "blocked"


# chat_id → role
_roles: dict[int, CommsRole] = {}


def set_role(chat_id: int, role: CommsRole):
    with _lock:
        _roles[chat_id] = role


def get_role(chat_id: int) -> CommsRole:
    with _lock:
        return _roles.get(chat_id, CommsRole.VIEWER)


def is_admin(chat_id: int) -> bool:
    return get_role(chat_id) == CommsRole.ADMIN


def is_viewer(chat_id: int) -> bool:
    return get_role(chat_id) in (CommsRole.ADMIN, CommsRole.VIEWER)


def promote_to_admin(chat_id: int, totp_code: str) -> bool:
    """Elevar a admin tras verificar TOTP."""
    try:
        from app.secrets_vault import verify_totp
        if verify_totp(totp_code):
            set_role(chat_id, CommsRole.ADMIN)
            logger.info("comms.auth: chat_id=%d promovido a ADMIN", chat_id)
            return True
    except Exception as e:
        logger.warning("comms.auth.promote: %s", e)
    return False


def require_admin(chat_id: int) -> bool:
    """Verificar que el usuario es admin; loguea intento si no."""
    if not is_admin(chat_id):
        logger.warning("comms.auth: acción de admin denegada a chat_id=%d", chat_id)
        return False
    return True


def list_roles() -> list[dict]:
    with _lock:
        return [{"chat_id": k, "role": v.value} for k, v in _roles.items()]
