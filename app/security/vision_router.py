"""
V-03: Router de visión — decide qué backend de análisis usar según la disponibilidad de GPU.

Estrategia (en orden):
  1. GPU libre → VLM local (llava / moondream)
  2. GPU ocupada → Pixtral cloud (Mistral API)
  3. Amenaza confirmada → siempre nube (garantía de calidad)
  4. Nube no disponible → vision_local.py (VLM tiny en CPU)

Gateado por SECURITY_ENABLED; si está en 0 el router responde con stub.
"""
from __future__ import annotations

import os
import threading

# V-07: métricas de uso de visión por backend (cuánto CPU vs GPU local vs nube).
_METRICS = {"local": 0, "cloud": 0, "cpu": 0, "blocked": 0, "disabled": 0, "total": 0}
_MLOCK = threading.Lock()


def _record(backend: str) -> None:
    bucket = ("cloud" if "cloud" in backend else
              "cpu" if "cpu" in backend else
              "blocked" if "blocked" in backend else
              "disabled" if backend == "disabled" else
              "local" if "local" in backend else "local")
    with _MLOCK:
        _METRICS[bucket] = _METRICS.get(bucket, 0) + 1
        _METRICS["total"] += 1


def metrics() -> dict:
    """V-07: reparto de análisis de visión por backend (local/nube/CPU)."""
    with _MLOCK:
        m = dict(_METRICS)
    tot = max(1, m["total"])
    m["local_pct"] = round(m["local"] / tot * 100, 1)
    m["cloud_pct"] = round(m["cloud"] / tot * 100, 1)
    m["cpu_pct"] = round(m["cpu"] / tot * 100, 1)
    return m


def _security_enabled() -> bool:
    return os.environ.get("CYBERAGENT_SECURITY_ENABLED", "0") == "1"


def route(
    image_b64: str,
    prompt: str = "Describe what you see.",
    is_threat: bool = False,
    force_cloud: bool = False,
) -> dict:
    """
    Analiza una imagen eligiendo el backend óptimo.

    Args:
        image_b64: imagen en base64 (JPEG/PNG)
        prompt: instrucción para el VLM
        is_threat: True → siempre usa cloud (alta calidad)
        force_cloud: True → usa cloud sin consultar GPU

    Returns:
        {"ok": bool, "text": str, "backend": str}
    """
    if not _security_enabled():
        _record("disabled")
        return {"ok": False, "text": "", "backend": "disabled",
                "error": "SECURITY_ENABLED=0"}

    from app.security.gpu_broker import is_security_blocked

    use_cloud = force_cloud or is_threat or is_security_blocked()

    if use_cloud:
        res = _run_cloud(image_b64, prompt)
    else:
        res = _run_local(image_b64, prompt)
        if not res["ok"]:
            res = _run_cloud(image_b64, prompt)
    _record(res.get("backend", "local"))
    return res


def _run_local(image_b64: str, prompt: str) -> dict:
    """VLM local via Ollama (llava/moondream)."""
    from app.security.gpu_broker import acquire_security, release_security
    model = os.environ.get("SECURITY_VLM_MODEL", "llava:7b")
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    if not acquire_security(timeout=2.0):
        return {"ok": False, "text": "", "backend": "local_blocked",
                "error": "GPU ocupada — degradando a nube"}
    try:
        import httpx
        r = httpx.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "images": [image_b64], "stream": False},
            timeout=30,
        )
        if r.status_code == 200:
            text = r.json().get("response", "")
            return {"ok": True, "text": text, "backend": "local_vlm", "model": model}
        return {"ok": False, "text": "", "backend": "local_vlm",
                "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "text": "", "backend": "local_vlm", "error": str(e)}
    finally:
        release_security()


def _run_cloud(image_b64: str, prompt: str) -> dict:
    """Pixtral via Mistral API."""
    try:
        from app.secrets_vault import get_secret
        api_key = get_secret("MISTRAL_API_KEY") or os.environ.get("MISTRAL_API_KEY")
    except Exception:
        api_key = os.environ.get("MISTRAL_API_KEY")

    if not api_key:
        return {"ok": False, "text": "", "backend": "cloud_pixtral",
                "error": "MISTRAL_API_KEY no configurada"}
    try:
        import httpx
        r = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "pixtral-12b-2409",
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": prompt},
                ]}],
                "max_tokens": 512,
            },
            timeout=30,
        )
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"]
            return {"ok": True, "text": text, "backend": "cloud_pixtral"}
        return {"ok": False, "text": "", "backend": "cloud_pixtral",
                "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "text": "", "backend": "cloud_pixtral", "error": str(e)}
