"""
PC → Cloud Run: envía alertas y solicitudes de aprobación.
Configura en .env o variables de entorno del sistema:
  CYBERAGENT_CLOUD_URL     https://cyberagent-xxx-uc.a.run.app
  CYBERAGENT_CLOUD_SECRET  tu-clave-secreta
"""
import os
import httpx

CLOUD_URL = os.environ.get("CYBERAGENT_CLOUD_URL", "").rstrip("/")
SECRET    = os.environ.get("CYBERAGENT_CLOUD_SECRET", "")
TIMEOUT   = 6


def _enabled() -> bool:
    return bool(CLOUD_URL and SECRET)


def _headers() -> dict:
    return {"X-Secret": SECRET, "Content-Type": "application/json"}


def send_threat_alert(title: str, body: str) -> bool:
    if not _enabled():
        return False
    try:
        httpx.post(
            f"{CLOUD_URL}/notify",
            json={"type": "threat", "title": title, "body": body},
            headers=_headers(),
            timeout=TIMEOUT,
        )
        return True
    except Exception as e:
        print(f"[alert] Error enviando amenaza: {e}")
        return False


def request_approval(tool_id: str, tool_name: str, args: dict) -> str:
    """Envía solicitud de aprobación. Devuelve el token o '' si falla."""
    if not _enabled():
        return ""
    try:
        r = httpx.post(
            f"{CLOUD_URL}/approval/request",
            json={"tool_id": tool_id, "tool_name": tool_name, "args": args},
            headers=_headers(),
            timeout=TIMEOUT,
        )
        return r.json().get("token", "")
    except Exception as e:
        print(f"[alert] Error enviando aprobación: {e}")
        return ""


def poll_approval(token: str) -> str | None:
    """Consulta el resultado. Devuelve 'approve', 'reject', o None si pendiente."""
    if not _enabled() or not token:
        return None
    try:
        r = httpx.get(
            f"{CLOUD_URL}/approval/{token}/poll",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        data = r.json()
        if data.get("status") == "decided":
            return data.get("decision", "reject")
    except Exception:
        pass
    return None


def cloud_configured() -> bool:
    return _enabled()
