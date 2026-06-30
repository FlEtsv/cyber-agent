"""
B-03: 2FA / auth para el bot de Telegram.

Flujo:
  1. Usuario escribe /start → bot pide código TOTP (si no es admin conocido).
  2. Usuario envía el código TOTP del authenticator.
  3. Si es válido → se registra como admin (primer user) o viewer.
  4. Admin puede añadir viewers con /addviewer <user_id>.

El TOTP usa la misma semilla del vault (SEC_TOTP_SECRET o TOTP_SECRET).
Si no hay TOTP configurado → solo se acepta el admin explícito (SEC_TELEGRAM_ADMIN_ID).
"""
from __future__ import annotations

import threading
import time

_pending: dict[int, float] = {}  # user_id → ts del challenge pendiente
_lock = threading.Lock()
_CHALLENGE_TTL = 120  # segundos para ingresar el código


def _totp_secret() -> str | None:
    try:
        from app.secrets_vault import get_secret
        return get_secret("SEC_TOTP_SECRET") or get_secret("TOTP_SECRET")
    except Exception:
        return None


def _admin_id() -> int | None:
    try:
        from app.secrets_vault import get_secret
        v = get_secret("SEC_TELEGRAM_ADMIN_ID") or get_secret("TELEGRAM_ADMIN_ID")
        return int(v) if v else None
    except Exception:
        return None


def verify_totp(code: str) -> bool:
    """Verifica código TOTP de 6 dígitos contra el secreto del vault."""
    secret = _totp_secret()
    if not secret:
        return False
    try:
        import pyotp
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:
        return False


def challenge(user_id: int) -> bool:
    """Lanza un challenge TOTP para user_id. Retorna True si hay secreto configurado."""
    if not _totp_secret():
        return False
    with _lock:
        _pending[user_id] = time.time()
    return True


def is_challenge_pending(user_id: int) -> bool:
    with _lock:
        ts = _pending.get(user_id)
    return bool(ts and time.time() - ts < _CHALLENGE_TTL)


def resolve_challenge(user_id: int, code: str, username: str = "") -> bool:
    """Intenta resolver el challenge con el código dado. True si éxito."""
    if not is_challenge_pending(user_id):
        return False
    if not verify_totp(code):
        return False
    with _lock:
        _pending.pop(user_id, None)

    from app.security.telegram.viewers import add_viewer, list_all
    existing = list_all()
    role = "admin" if not existing else "viewer"
    add_viewer(user_id, username, role)
    return True


def is_authorized_user(user_id: int) -> bool:
    """True si el user está registrado O es el admin hardcoded."""
    admin = _admin_id()
    if admin and user_id == admin:
        return True
    from app.security.telegram.viewers import is_authorized
    return is_authorized(user_id)


def is_admin_user(user_id: int) -> bool:
    admin = _admin_id()
    if admin and user_id == admin:
        return True
    from app.security.telegram.viewers import is_admin
    return is_admin(user_id)
