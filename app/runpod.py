"""
Control del Pod de RunPod (gpt-oss-120b en A100) — encender/apagar/estado y el
endpoint OpenAI-compatible de vLLM.

El pod cuesta dinero por hora, así que solo se enciende bajo demanda y se apaga
por inactividad. La app es el mando: usa la API GraphQL de RunPod.

Config por entorno (.env del PC):
  RUNPOD_API_KEY   → API key de tu cuenta RunPod (para start/stop/status)
  RUNPOD_POD_ID    → id del pod ya creado (con Network Volume en /workspace)
  VLLM_API_KEY     → la api-key con la que arranca vLLM en el pod
  RUNPOD_MODEL     → served-model-name (default: gpt-oss-120b)
  RUNPOD_BASE_URL  → (opcional) override del endpoint OpenAI; si no, se deriva
                     del POD_ID: https://<POD_ID>-8000.proxy.runpod.net/v1
"""
from __future__ import annotations

import os
import time

import httpx

_GQL = "https://api.runpod.io/graphql"


def api_key() -> str:
    return (os.getenv("RUNPOD_API_KEY") or "").strip()


def pod_id() -> str:
    return (os.getenv("RUNPOD_POD_ID") or "").strip()


def vllm_key() -> str:
    return (os.getenv("VLLM_API_KEY") or "").strip()


def model_name() -> str:
    return (os.getenv("RUNPOD_MODEL") or "gpt-oss-120b").strip()


def available() -> bool:
    """True si la app puede controlar el pod (hay API key + pod id)."""
    return bool(api_key() and pod_id())


def base_url() -> str:
    """Endpoint OpenAI-compatible de vLLM en el pod."""
    override = (os.getenv("RUNPOD_BASE_URL") or "").strip()
    if override:
        return override.rstrip("/")
    return f"https://{pod_id()}-8000.proxy.runpod.net/v1"


def _gql(query: str, variables: dict | None = None) -> dict:
    key = api_key()
    if not key:
        return {"ok": False, "error": "RUNPOD_API_KEY no configurada"}
    try:
        r = httpx.post(f"{_GQL}?api_key={key}",
                       json={"query": query, "variables": variables or {}},
                       timeout=30)
        if r.status_code >= 400:
            return {"ok": False, "error": f"RunPod HTTP {r.status_code}: {r.text[:300]}"}
        data = r.json()
        if data.get("errors"):
            return {"ok": False, "error": str(data["errors"])[:300]}
        return {"ok": True, "data": data.get("data", {})}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def pod_status() -> dict:
    """Estado del pod: desiredStatus (RUNNING/EXITED/...) y si el endpoint responde."""
    if not available():
        return {"ok": False, "error": "RunPod no configurado (RUNPOD_API_KEY/RUNPOD_POD_ID)"}
    q = """query($id: String!) { pod(input: {podId: $id}) {
        id name desiredStatus
        runtime { uptimeInSeconds ports { publicPort privatePort type } }
    } }"""
    res = _gql(q, {"id": pod_id()})
    if not res.get("ok"):
        return res
    pod = (res["data"] or {}).get("pod") or {}
    return {"ok": True, "status": pod.get("desiredStatus", "UNKNOWN"),
            "uptime": (pod.get("runtime") or {}).get("uptimeInSeconds"),
            "running": pod.get("desiredStatus") == "RUNNING"}


def start_pod() -> dict:
    """Reanuda el pod (lo enciende). Idempotente si ya está RUNNING."""
    if not available():
        return {"ok": False, "error": "RunPod no configurado"}
    st = pod_status()
    if st.get("ok") and st.get("running"):
        return {"ok": True, "status": "RUNNING", "already": True}
    q = """mutation($id: String!) { podResume(input: {podId: $id, gpuCount: 1}) {
        id desiredStatus } }"""
    res = _gql(q, {"id": pod_id()})
    if not res.get("ok"):
        return res
    pod = (res["data"] or {}).get("podResume") or {}
    return {"ok": True, "status": pod.get("desiredStatus", "STARTING")}


def stop_pod() -> dict:
    """Para el pod (deja de facturar el GPU). El Network Volume se conserva."""
    if not available():
        return {"ok": False, "error": "RunPod no configurado"}
    q = """mutation($id: String!) { podStop(input: {podId: $id}) {
        id desiredStatus } }"""
    res = _gql(q, {"id": pod_id()})
    if not res.get("ok"):
        return res
    pod = (res["data"] or {}).get("podStop") or {}
    return {"ok": True, "status": pod.get("desiredStatus", "EXITED")}


def endpoint_ready(timeout: float = 4.0) -> bool:
    """¿Responde ya el /v1/models de vLLM?"""
    try:
        headers = {}
        if vllm_key():
            headers["Authorization"] = f"Bearer {vllm_key()}"
        r = httpx.get(f"{base_url()}/models", headers=headers, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def ensure_running(max_wait: float = 180.0, on_status=None) -> dict:
    """Garantiza pod encendido y vLLM sirviendo. Arranca si hace falta y espera.
    `on_status(msg)` opcional para feedback en vivo."""
    def _say(m):
        if on_status:
            try:
                on_status(m)
            except Exception:
                pass
    if not available():
        return {"ok": False, "error": "RunPod no configurado"}
    if endpoint_ready():
        return {"ok": True, "status": "RUNNING"}
    _say("☁️ Encendiendo el pod RunPod (A100)…")
    s = start_pod()
    if not s.get("ok"):
        return s
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if endpoint_ready(timeout=4.0):
            _say("✅ Pod listo (vLLM sirviendo gpt-oss-120b).")
            return {"ok": True, "status": "RUNNING"}
        _say("⏳ Esperando a que vLLM cargue el modelo…")
        time.sleep(6)
    return {"ok": False, "error": "timeout esperando a vLLM en el pod"}
