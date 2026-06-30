"""
E-01..E-05: Herramientas Home Assistant para el agente.

Dispatcher unificado bajo la tool `ha_control`. Gateado: requiere
SEC_HA_URL + SEC_HA_TOKEN en el vault (secretos del módulo de seguridad).
Todas las ops son DANGEROUS (controlan dispositivos reales).
"""
from __future__ import annotations

import httpx

_MAX_OUT = 4000


def _cfg() -> tuple[str, str]:
    from app.secrets_vault import get_secret
    url = (get_secret("SEC_HA_URL") or "").rstrip("/")
    token = get_secret("SEC_HA_TOKEN") or ""
    return url, token


def available() -> bool:
    try:
        url, token = _cfg()
        return bool(url and token)
    except Exception:
        return False


def _call(method: str, path: str, *, data: dict | None = None, timeout: int = 15) -> dict:
    url, token = _cfg()
    if not url or not token:
        return {"ok": False, "error": "SEC_HA_URL o SEC_HA_TOKEN no configurados en el vault"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = httpx.request(
            method, f"{url}{path}",
            json=data, headers=headers, timeout=timeout,
        )
        if resp.status_code in (200, 201):
            try:
                return {"ok": True, "data": resp.json()}
            except Exception:
                return {"ok": True, "data": resp.text[:_MAX_OUT]}
        return {"ok": False, "status": resp.status_code, "error": resp.text[:_MAX_OUT]}
    except httpx.TimeoutException:
        return {"ok": False, "error": f"timeout ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ── E-01: control de entidad ─────────────────────────────────────────────────

def ha_control(entity_id: str, service: str = "turn_on", data: dict | None = None) -> dict:
    """Llama a un servicio HA sobre una entidad (luz IR, autofoco, interruptores…)."""
    if not entity_id:
        return {"ok": False, "error": "entity_id requerido"}
    domain = entity_id.split(".")[0] if "." in entity_id else entity_id
    payload: dict = {"entity_id": entity_id}
    if data:
        payload.update(data)
    return _call("POST", f"/api/services/{domain}/{service}", data=payload)


# ── E-02: TTS ────────────────────────────────────────────────────────────────

def ha_speak(message: str, media_player: str | None = None, language: str = "es") -> dict:
    """Reproduce un mensaje de voz en el altavoz vía TTS de HA."""
    if not message:
        return {"ok": False, "error": "message requerido"}
    payload = {
        "entity_id": media_player or "media_player.all",
        "message": message,
        "language": language,
    }
    return _call("POST", "/api/services/tts/speak", data=payload)


# ── E-03: cámara ─────────────────────────────────────────────────────────────

def ha_camera(camera_entity: str, op: str = "snapshot") -> dict:
    """Snapshot o estado de una cámara HA."""
    if not camera_entity:
        return {"ok": False, "error": "camera_entity requerido"}
    if op == "snapshot":
        url, _ = _cfg()
        return {
            "ok": True,
            "info": "Snapshot disponible",
            "url": f"{url}/api/camera_proxy/{camera_entity}",
        }
    if op == "state":
        return _call("GET", f"/api/states/{camera_entity}")
    return {"ok": False, "error": f"op desconocida: {op} (válidas: snapshot, state)"}


# ── E-04: script ─────────────────────────────────────────────────────────────

def ha_script(script_id: str, data: dict | None = None) -> dict:
    """Ejecuta un script de HA (reboot, sync_clock, genérico)."""
    if not script_id:
        return {"ok": False, "error": "script_id requerido"}
    full_id = script_id if "." in script_id else f"script.{script_id}"
    payload: dict = {"entity_id": full_id}
    if data:
        payload.update(data)
    return _call("POST", "/api/services/script/turn_on", data=payload)


# ── Dispatcher principal (E-05 lo registra en tools.py) ─────────────────────

def run(op: str, entity_id: str = "", params: dict | None = None) -> dict:
    """
    Dispatcher unificado `ha_control` del agente.

    op:
      turn_on / turn_off / toggle / call   → ha_control (service = op o params.service)
      speak                                 → ha_speak (params.message / params.media_player)
      snapshot                              → ha_camera snapshot
      camera_state                          → ha_camera state
      script                                → ha_script (entity_id = script id)
      state                                 → GET /api/states/{entity_id}
      states                                → GET /api/states (lista todas)
      services                              → GET /api/services (catálogo de dominios)
      ping                                  → GET /api/ (comprueba conectividad HA)
    """
    p = params or {}
    op = (op or "").lower().strip()

    if op in ("turn_on", "turn_off", "toggle", "call", "control"):
        svc = p.get("service", op) if op != "control" else "turn_on"
        return ha_control(entity_id, svc, p.get("data"))

    if op == "speak":
        msg = p.get("message") or entity_id
        return ha_speak(msg, p.get("media_player"), p.get("language", "es"))

    if op == "snapshot":
        return ha_camera(entity_id, "snapshot")

    if op == "camera_state":
        return ha_camera(entity_id, "state")

    if op == "script":
        return ha_script(entity_id, p.get("data"))

    if op == "state":
        return _call("GET", f"/api/states/{entity_id}")

    if op == "states":
        return _call("GET", "/api/states")

    if op == "services":
        return _call("GET", "/api/services")

    if op == "ping":
        return _call("GET", "/api/")

    return {
        "ok": False,
        "error": (
            f"op HA desconocida: '{op}' — válidas: "
            "turn_on / turn_off / toggle / call / speak / snapshot / camera_state / script / state / states / services / ping"
        ),
    }
