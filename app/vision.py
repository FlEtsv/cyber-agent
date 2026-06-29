"""
Interpretación de imágenes (visión) — fuente única para TODA la app.

Orden de preferencia (sin gastar GPU del modelo principal si no hace falta):
  1. Modelo de visión LOCAL en Ollama (llava / qwen2-vl / moondream / bakllava).
  2. Mistral **Pixtral** en la nube (pixtral-large-latest) si hay API key.
  3. Mensaje claro si no hay ninguna opción disponible.

Lo usan el WebSocket local (`server.py`) y el puente del relay
(`relay_connector.py`) para que adjuntar imágenes funcione igual desde el PC y
desde la web/móvil.
"""
from __future__ import annotations

import httpx

_OLLAMA = "http://localhost:11434"
_VISION_KEYWORDS = ("llava", "vision", "moondream", "bakllava", "qwen2-vl", "qwen2.5-vl", "pixtral")
_PIXTRAL_MODEL = "pixtral-large-latest"

_DEFAULT_PROMPT = (
    "Describe detalladamente lo que ves en esta imagen. Incluye: texto visible, "
    "elementos de interfaz, objetos, colores, contexto y cualquier información "
    "relevante. Responde en español."
)


def _strip_data_url(b64: str) -> str:
    return b64.split(",", 1)[1] if "," in b64 else b64


async def _local_vision_model() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{_OLLAMA}/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]
        return next((m for m in models
                     if any(k in m.lower() for k in _VISION_KEYWORDS)), None)
    except Exception:
        return None


async def _describe_local(b64: str, model: str, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{_OLLAMA}/api/generate", json={
            "model": model,
            "prompt": prompt,
            "images": [b64],
            "stream": False,
        })
    return r.json().get("response", "").strip() or "[no se pudo describir la imagen]"


async def _describe_pixtral(b64: str, prompt: str) -> str | None:
    """Interpreta la imagen con Mistral Pixtral (nube). Devuelve None si no hay key."""
    try:
        from app.mistral_client import _api_key
        key = _api_key()
    except Exception:
        key = ""
    if not key:
        return None
    data_uri = f"data:image/jpeg;base64,{b64}"
    payload = {
        "model": _PIXTRAL_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": data_uri},
            ],
        }],
        "max_tokens": 900,
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(timeout=90) as c:
            r = await c.post(
                "https://api.mistral.ai/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
        if r.status_code >= 400:
            return f"[visión Pixtral HTTP {r.status_code}]"
        out = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(out, list):  # algunos formatos devuelven lista de bloques
            out = " ".join(str(p.get("text", "")) for p in out if isinstance(p, dict))
        try:
            from app import mistral_usage
            usage = r.json().get("usage", {}) or {}
            mistral_usage.log_usage(_PIXTRAL_MODEL,
                                    usage.get("prompt_tokens", 0),
                                    usage.get("completion_tokens", 0), "vision")
        except Exception:
            pass
        return (out or "").strip() or "[Pixtral no devolvió descripción]"
    except Exception as e:
        return f"[visión Pixtral error: {e}]"


async def describe_image(b64: str, prompt: str | None = None) -> str:
    """Describe una imagen (base64, con o sin prefijo data:). Local → Pixtral → aviso."""
    b64 = _strip_data_url(b64)
    prompt = prompt or _DEFAULT_PROMPT

    model = await _local_vision_model()
    if model and "pixtral" not in model.lower():
        try:
            return await _describe_local(b64, model, prompt)
        except Exception:
            pass  # caemos a la nube

    cloud = await _describe_pixtral(b64, prompt)
    if cloud is not None:
        return cloud

    return ("[imagen adjunta — no hay visión disponible: instala un modelo local "
            "(p. ej. `ollama pull llava`) o configura MISTRAL_API_KEY para usar Pixtral]")


async def describe_images(b64_list: list[str], prompt: str | None = None, limit: int = 3) -> str:
    """Describe varias imágenes y las une en un bloque para inyectar en el prompt."""
    descs: list[str] = []
    for b64 in (b64_list or [])[:limit]:
        descs.append(await describe_image(b64, prompt))
    if not descs:
        return ""
    return "\n\n[Imágenes compartidas]\n" + "\n\n---\n\n".join(descs)
