"""
D-07: app_registry — registro de aplicaciones externas que pueden enviar eventos.

Cada app externa se identifica con un token único (SEC_EVENT_TOKEN o derivado).
El token se valida en security_routes.py (X-Event-Token header).
"""
from __future__ import annotations

import json
import logging
import secrets
import time
from pathlib import Path

logger = logging.getLogger(__name__)
_REGISTRY_PATH = Path("data/app_registry.json")


def _load() -> dict:
    if _REGISTRY_PATH.exists():
        try:
            return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"apps": {}}


def _save(data: dict) -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def register_app(name: str, description: str = "", token: str | None = None) -> dict:
    """Registra una app externa y retorna su token."""
    data = _load()
    t = token or secrets.token_hex(24)
    data["apps"][name] = {
        "token": t,
        "description": description,
        "registered_at": time.time(),
        "active": True,
    }
    _save(data)
    logger.info("app_registry: app '%s' registrada", name)
    return {"name": name, "token": t}


def revoke_app(name: str) -> bool:
    data = _load()
    if name in data.get("apps", {}):
        data["apps"][name]["active"] = False
        _save(data)
        return True
    return False


def validate_token(token: str) -> str | None:
    """Retorna el nombre de la app si el token es válido, None si no."""
    # Token global del vault
    try:
        from app.secrets_vault import get_secret
        global_token = get_secret("SEC_EVENT_TOKEN")
        if global_token and token == global_token:
            return "global"
    except Exception:
        pass

    data = _load()
    for name, info in data.get("apps", {}).items():
        if info.get("active") and info.get("token") == token:
            return name
    return None


def list_apps() -> list[dict]:
    data = _load()
    return [
        {"name": k, "description": v.get("description", ""), "active": v.get("active", False)}
        for k, v in data.get("apps", {}).items()
    ]
