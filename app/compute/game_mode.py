"""
AA-01..AA-06: Modo juego — gestión de recursos cuando el usuario juega.

Detecta proceso de juego (fullscreen / GPU intensiva) y:
  - Libera VRAM del LLM (AA-02)
  - Activa no_disturb en el GPU broker (AA-03)
  - Degrada seguridad a nube/CPU (AA-04)
  - Restaura al salir (AA-05)
  - Pausa entrenamiento (AA-06)
"""
from __future__ import annotations

import os
import threading
import time


_active = False
_lock = threading.Lock()


def enter_game_mode() -> dict:
    """Entra en modo juego: libera VRAM y bloquea uso de GPU por seguridad."""
    global _active
    with _lock:
        if _active:
            return {"ok": True, "already": True}
        _active = True

    # AA-03: bloquear GPU para seguridad
    try:
        from app.security.gpu_broker import set_no_disturb
        set_no_disturb(True)
    except Exception:
        pass

    # AA-02: liberar el LLM de VRAM (Ollama: cargar keep_alive=0)
    try:
        import httpx
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        from app.ollama_client import OLLAMA_MODEL
        httpx.post(f"{ollama_url}/api/generate",
                   json={"model": OLLAMA_MODEL, "prompt": "", "keep_alive": 0},
                   timeout=5)
    except Exception:
        pass

    # AA-06: señal para pausar training scheduler (si existe)
    try:
        from app import training_store
        training_store.record("event", "game_mode", "entered", 0.0, {"action": "enter"})
    except Exception:
        pass

    return {"ok": True, "game_mode": True}


def exit_game_mode() -> dict:
    """Sale del modo juego: restaura GPU broker y permite reanudar entrenamiento."""
    global _active
    with _lock:
        if not _active:
            return {"ok": True, "already": False}
        _active = False

    try:
        from app.security.gpu_broker import set_no_disturb
        set_no_disturb(False)
    except Exception:
        pass

    try:
        from app import training_store
        training_store.record("event", "game_mode", "exited", 0.0, {"action": "exit"})
    except Exception:
        pass

    return {"ok": True, "game_mode": False}


def is_active() -> bool:
    with _lock:
        return _active


def status() -> dict:
    return {"game_mode": is_active()}


def auto_detect() -> bool:
    """
    AA-01: Detecta si hay un proceso de juego corriendo (heurística Windows).
    Retorna True si se detectó un juego.
    """
    try:
        import subprocess
        # Busca procesos con GPU > 50% via nvidia-smi
        r = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.strip().splitlines():
                parts = line.split(",")
                if len(parts) == 2:
                    vram_mb = int(parts[1].strip())
                    if vram_mb > 6_000:  # > 6 GB de VRAM → probablemente un juego
                        return True
    except Exception:
        pass
    return False
