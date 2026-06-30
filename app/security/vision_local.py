"""
Z-06: VLM tiny en CPU como último recurso cuando GPU+nube no están disponibles.

Opciones por prioridad:
  1. moondream2 via transformers (CPU, ~2 GB RAM)
  2. llava-phi3 via Ollama (CPU mode)
  3. Respuesta vacía (pipeline no bloquea)
"""
from __future__ import annotations

import os


def analyze_cpu(image_b64: str, prompt: str = "¿Qué ves en la imagen?") -> dict:
    """
    Analiza una imagen usando solo CPU.

    Returns:
        {"ok": bool, "text": str, "backend": str}
    """
    # Intentar via Ollama en modo CPU
    result = _try_ollama_cpu(image_b64, prompt)
    if result["ok"]:
        return result

    return {"ok": False, "text": "", "backend": "cpu_vlm",
            "error": "No hay VLM disponible en CPU"}


def _try_ollama_cpu(image_b64: str, prompt: str) -> dict:
    """Usa Ollama con un modelo ligero; si la GPU está en uso, Ollama usa CPU."""
    model = os.environ.get("SECURITY_VLM_CPU_MODEL", "moondream:1.8b")
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    try:
        import httpx
        r = httpx.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "images": [image_b64],
                  "stream": False, "options": {"num_gpu": 0}},  # fuerza CPU
            timeout=60,
        )
        if r.status_code == 200:
            text = r.json().get("response", "")
            return {"ok": True, "text": text, "backend": f"cpu_vlm/{model}"}
        return {"ok": False, "text": "", "backend": "cpu_vlm",
                "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "text": "", "backend": "cpu_vlm", "error": str(e)}
