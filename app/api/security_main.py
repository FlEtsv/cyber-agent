"""
Entry-point standalone para el contenedor Docker de seguridad.

Monta solo los routers de seguridad (no el servidor completo de CyberAgent)
para poder desplegar el módulo de seguridad de forma independiente.

Arranca en :8766.
"""
from __future__ import annotations

import os
import threading

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="CyberAgent Security", docs_url=None, redoc_url=None)

# Router de seguridad
from app.api.security_routes import router as _sec_router
app.include_router(_sec_router)


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "cyberagent-sec"})


@app.on_event("startup")
def _startup() -> None:
    """Arranca servicios de seguridad al iniciar el servidor."""
    os.environ.setdefault("SECURITY_ENABLED", "1")

    # Bot Telegram
    try:
        from app.security.telegram.bot import start as bot_start
        bot_start()
    except Exception as e:
        print(f"[security_main] TelegramBot no arrancado: {e}")

    # Motor de eventos
    try:
        from app.security.events import start as ev_start
        ev_start()
    except Exception as e:
        print(f"[security_main] Events no arrancado: {e}")

    # Tareas programadas en background
    def _sched_loop():
        import time
        from app.security.schedule import run_due, default_tasks
        default_tasks()
        while True:
            try:
                run_due()
            except Exception:
                pass
            time.sleep(60)

    threading.Thread(target=_sched_loop, name="SecuritySchedule", daemon=True).start()
    print("[security_main] CyberAgent Security arrancado (puerto 8766)")
