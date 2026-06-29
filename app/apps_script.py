"""
Puente con Google Apps Script (WEBPROD-016).

Llama a la webapp de Apps Script que Steve despliega en su cuenta para ejecutar
acciones AVANZADAS de Workspace bajo demanda: crear/modificar Sheets, Docs,
Slides, gestionar Gmail/Drive/Calendar, o ejecutar código Apps Script arbitrario
(op="exec") cuando el usuario lo pide.

Config por entorno (lo pone Steve tras desplegar la webapp):
  APPS_SCRIPT_URL     → URL .../exec de la implementación
  APPS_SCRIPT_SECRET  → el mismo secreto que en Script Properties (SHARED_SECRET)

Es una acción SENSIBLE: la tool `apps_script` está en DANGEROUS_TOOLS, así que el
agente pide aprobación (consentimiento) antes de tocar tu cuenta.
"""
from __future__ import annotations

import os

import httpx


def available() -> bool:
    return bool(os.getenv("APPS_SCRIPT_URL") and os.getenv("APPS_SCRIPT_SECRET"))


def run(op: str = "", params: dict | None = None, code: str = "") -> dict:
    """Ejecuta una operación del catálogo (op) o código arbitrario (op='exec', code=...)."""
    url = os.getenv("APPS_SCRIPT_URL", "").strip()
    secret = os.getenv("APPS_SCRIPT_SECRET", "").strip()
    if not url or not secret:
        return {"ok": False, "error": (
            "Apps Script no configurado. Despliega la webapp (integrations/apps_script/"
            "Code.gs) y define APPS_SCRIPT_URL y APPS_SCRIPT_SECRET. Ver docs/SETUP_GOOGLE.md.")}
    payload = {"secret": secret, "op": (op or "").strip(), "params": params or {}}
    if code:
        payload["code"] = code
    try:
        r = httpx.post(url, json=payload,
                       timeout=httpx.Timeout(connect=10, read=120, write=20, pool=10),
                       follow_redirects=True)
        if r.status_code >= 400:
            return {"ok": False, "error": f"Apps Script HTTP {r.status_code}: {r.text[:300]}"}
        data = r.json()
        if not data.get("ok"):
            return {"ok": False, "error": data.get("error", "error desconocido")}
        return {"ok": True, "op": data.get("op", op), "result": data.get("result")}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
