"""
Gestor de secretos LOCAL de CyberAgent.

Guarda cifrado (Fernet) las claves del sistema — las DOS de Mistral (la de
CyberAgent y la de APiComunicaciones), tokens de Telegram, Home Assistant,
EVENT_TOKEN, etc. — en data/vault.enc. La clave de cifrado vive en data/.vault_key
(local). Revelar valores en la web exige un código TOTP válido (authenticator).

Para el resto del sistema: get_secret("MISTRAL_API_KEY") devuelve el valor en
claro para usarlo (p.ej. el módulo de seguridad → Mistral nube de cámaras).
"""
from __future__ import annotations

import json
import os
import threading

from cryptography.fernet import Fernet

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_VAULT = os.path.join(_DATA, "vault.enc")
_KEYFILE = os.path.join(_DATA, ".vault_key")
_LOCK = threading.Lock()
_CACHE: dict | None = None


def _fernet() -> Fernet:
    os.makedirs(_DATA, exist_ok=True)
    if not os.path.isfile(_KEYFILE):
        with open(_KEYFILE, "wb") as f:
            f.write(Fernet.generate_key())
        try:
            os.chmod(_KEYFILE, 0o600)
        except Exception:
            pass
    with open(_KEYFILE, "rb") as f:
        return Fernet(f.read().strip())


def _load() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not os.path.isfile(_VAULT):
        _CACHE = {}
        return _CACHE
    try:
        raw = _fernet().decrypt(open(_VAULT, "rb").read())
        _CACHE = json.loads(raw.decode("utf-8"))
    except Exception:
        _CACHE = {}
    return _CACHE


def _save(data: dict) -> None:
    global _CACHE
    blob = _fernet().encrypt(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    os.makedirs(_DATA, exist_ok=True)
    with open(_VAULT, "wb") as f:
        f.write(blob)
    _CACHE = data


# ── API pública ───────────────────────────────────────────────────────────────
def get_secret(name: str, default: str | None = None) -> str | None:
    with _LOCK:
        return _load().get(name, default)


def set_secret(name: str, value: str) -> None:
    with _LOCK:
        data = dict(_load())
        data[name] = value
        _save(data)


def delete_secret(name: str) -> bool:
    with _LOCK:
        data = dict(_load())
        if name in data:
            del data[name]
            _save(data)
            return True
        return False


def list_secrets_masked() -> list[dict]:
    """Nombres + valor enmascarado (para la web sin revelar). No requiere 2FA."""
    with _LOCK:
        out = []
        for k, v in sorted(_load().items()):
            v = v or ""
            mask = (v[:3] + "…" + v[-2:]) if len(v) > 8 else ("••••" if v else "(vacío)")
            out.append({"name": k, "masked": mask, "empty": not v})
        return out


def reveal_all(totp_code: str) -> dict:
    """Devuelve TODOS los secretos en claro SOLO si el código TOTP es válido."""
    if not _verify_totp(totp_code):
        return {"ok": False, "error": "Código de autenticación inválido"}
    with _LOCK:
        return {"ok": True, "secrets": dict(_load())}


def _verify_totp(code: str) -> bool:
    """Verifica el código contra el TOTP del relay (RELAY_TOTP_SECRET) o el del
    vault (VAULT_TOTP_SECRET). Reutiliza el authenticator que ya usas."""
    code = (code or "").strip().replace(" ", "")
    secret = (os.environ.get("VAULT_TOTP_SECRET")
              or os.environ.get("RELAY_TOTP_SECRET")
              or get_secret("RELAY_TOTP_SECRET") or "")
    if not secret or not code:
        return False
    try:
        import pyotp
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:
        return False


def import_env(env_path: str, prefix_skip=("#",)) -> int:
    """Importa un .env al vault (para traer los secretos reales de APiComuni).
    Devuelve cuántas claves nuevas se guardaron."""
    if not os.path.isfile(env_path):
        return 0
    n = 0
    with _LOCK:
        data = dict(_load())
        for line in open(env_path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k and k not in data:
                data[k] = v
                n += 1
        _save(data)
    return n
