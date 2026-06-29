"""
Integración de las herramientas nativas de Mistral Studio (connectors).

Usa la API de Conversations de Mistral para dar al agente acceso a:
  - web_search        → búsqueda web real con citaciones
  - code_interpreter  → ejecuta Python en el sandbox de Mistral y devuelve salida/figuras
  - image_generation  → genera imágenes (FLUX) y las descarga localmente
  - document_library  → RAG sobre librerías de documentos subidas a Mistral

Parseo defensivo: el formato de `outputs` puede variar, así que recorremos la
estructura buscando texto, referencias de archivos e imágenes.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx

from app.brain import MISTRAL_BASE_URL, mistral_api_key, mistral_available

# Importar el monitor de consumo
def log_usage(input_tokens, output_tokens, context=""):
    """Registra el consumo de los connectors en el contador unificado (mistral_usage)
    para que TODO el gasto de Mistral sea visible. Nota: web_search/code_interpreter/
    image_generation tienen recargos por uso que aquí solo se estiman por tokens."""
    try:
        from app import mistral_usage
        mistral_usage.log_usage("mistral-studio", input_tokens, output_tokens, "studio:" + str(context))
    except Exception:
        pass

# carpeta pública donde dejamos imágenes/artefactos generados
_SERVED_DIR = os.path.join(os.path.dirname(__file__), "web", "served")

_CONNECTOR_ALIASES = {
    "web": "web_search",
    "search": "web_search",
    "web_search": "web_search",
    "code": "code_interpreter",
    "code_interpreter": "code_interpreter",
    "python": "code_interpreter",
    "image": "image_generation",
    "image_generation": "image_generation",
    "imagen": "image_generation",
    "docs": "document_library",
    "document_library": "document_library",
}


def available() -> bool:
    return mistral_available()


def _ensure_served() -> str:
    os.makedirs(_SERVED_DIR, exist_ok=True)
    return _SERVED_DIR


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {mistral_api_key()}",
        "Content-Type": "application/json",
    }


def _download_file(file_id: str) -> str | None:
    """Descarga un archivo generado (imagen) por su id y devuelve la ruta local."""
    try:
        url = f"{MISTRAL_BASE_URL}/files/{file_id}/content"
        r = httpx.get(url, headers={"Authorization": f"Bearer {mistral_api_key()}"}, timeout=60)
        if r.status_code != 200:
            return None
        ext = ".png"
        ctype = r.headers.get("content-type", "")
        if "jpeg" in ctype:
            ext = ".jpg"
        elif "webp" in ctype:
            ext = ".webp"
        _ensure_served()
        name = f"mistral_{file_id[:16]}{ext}"
        path = os.path.join(_SERVED_DIR, name)
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception:
        return None


def _walk_outputs(outputs: Any, texts: list[str], files: list[str], tools: list[str]) -> None:
    """Recorre recursivamente la estructura de salida acumulando texto/archivos/tools."""
    if isinstance(outputs, dict):
        otype = outputs.get("type", "")
        if otype in ("tool.execution", "function.call") and outputs.get("name"):
            tools.append(outputs["name"])
        # texto directo
        for key in ("text", "content"):
            val = outputs.get(key)
            if isinstance(val, str) and val.strip():
                texts.append(val.strip())
            elif isinstance(val, list):
                _walk_outputs(val, texts, files, tools)
        # referencias a archivos/imágenes
        fid = outputs.get("file_id") or outputs.get("file") or outputs.get("id")
        if otype in ("tool_file", "image", "image_generation", "file") and isinstance(fid, str):
            p = _download_file(fid)
            if p:
                files.append(p)
        for v in outputs.values():
            if isinstance(v, (list, dict)):
                _walk_outputs(v, texts, files, tools)
    elif isinstance(outputs, list):
        for item in outputs:
            _walk_outputs(item, texts, files, tools)


def _estimate_tokens(text: str) -> int:
    """Estima tokens a partir del texto (1 token ≈ 0.75 palabras)."""
    words = len(text.split())
    return int(words * 1.33)


def run(
    prompt: str,
    connectors: list[str] | None = None,
    model: str | None = None,
    library_ids: list[str] | None = None,
    max_tokens: int = 2048,
) -> dict:
    """
    Lanza una conversación de Mistral con connectors nativos.
    Devuelve {ok, text, files:[rutas], tools_used:[...], model}.
    """
    if not mistral_available():
        return {"ok": False, "error": "MISTRAL_API_KEY no configurada"}

    connectors = connectors or ["web_search"]
    norm: list[str] = []
    for c in connectors:
        key = _CONNECTOR_ALIASES.get(str(c).strip().lower())
        if key and key not in norm:
            norm.append(key)
    if not norm:
        norm = ["web_search"]

    tools: list[dict] = []
    for c in norm:
        if c == "document_library":
            tools.append({"type": "document_library",
                          "library_ids": library_ids or []})
        else:
            tools.append({"type": c})

    real_model = model or os.getenv("CYBERAGENT_MISTRAL_MODEL", "mistral-medium-latest")
    payload = {
        "model": real_model,
        "inputs": prompt,
        "tools": tools,
        "stream": False,
        "completion_args": {"max_tokens": max(256, min(int(max_tokens), 8192))},
    }

    try:
        r = httpx.post(
            f"{MISTRAL_BASE_URL}/conversations",
            json=payload, headers=_headers(),
            timeout=httpx.Timeout(connect=10, read=180, write=30, pool=10),
        )
        if r.status_code >= 400:
            return {"ok": False, "error": f"Mistral HTTP {r.status_code}: {r.text[:500]}",
                    "model": real_model, "connectors": norm}
        data = r.json()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "model": real_model, "connectors": norm}

    texts: list[str] = []
    files: list[str] = []
    tused: list[str] = []
    _walk_outputs(data.get("outputs", data), texts, files, tused)
    # de-duplicar fragmentos de texto repetidos preservando el orden
    seen: set[str] = set()
    texts = [t for t in texts if not (t in seen or seen.add(t))]

    # publicar archivos por URL si hay túnel
    served = []
    if files:
        try:
            from app.documents import public_url_for
            for p in files:
                served.append({"path": p, "url": public_url_for(p)})
        except Exception:
            served = [{"path": p, "url": ""} for p in files]

    # Estimar tokens y registrar consumo
    input_tokens = _estimate_tokens(prompt)
    output_text = "\n\n".join(texts).strip() or "(sin texto en la respuesta)"
    output_tokens = _estimate_tokens(output_text)
    log_usage(input_tokens, output_tokens, context=",".join(norm))

    return {
        "ok": True,
        "model": real_model,
        "connectors": norm,
        "tools_used": sorted(set(tused)),
        "text": output_text,
        "files": served,
        "conversation_id": data.get("conversation_id") or data.get("id"),
    }