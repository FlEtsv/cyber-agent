"""
Z-01: Perfil de recursos del sistema + presupuesto por subsistema.

Detecta la RAM disponible, núcleos de CPU y GPU VRAM en tiempo real.
Define presupuestos máximos por subsistema para evitar contención.
"""
from __future__ import annotations

import os


# Presupuestos configurables (en MB y núcleos)
BUDGETS = {
    "agent":    {"ram_mb": 8_000,  "cpu_cores": 4},   # LLM del usuario
    "security": {"ram_mb": 4_000,  "cpu_cores": 2},   # visión + detección
    "rag":      {"ram_mb": 2_000,  "cpu_cores": 2},   # embeddings + búsqueda
    "training": {"ram_mb": 16_000, "cpu_cores": 4},   # QLoRA (batch background)
    "cache":    {"ram_mb": 8_000,  "cpu_cores": 0},   # RAM cache frames/embeddings
}


def system_info() -> dict:
    """Retorna RAM total/libre, núcleos y VRAM si está disponible."""
    info: dict = {}
    try:
        import psutil
        vm = psutil.virtual_memory()
        info["ram_total_mb"] = vm.total // (1024 * 1024)
        info["ram_available_mb"] = vm.available // (1024 * 1024)
        info["ram_used_pct"] = vm.percent
        info["cpu_cores"] = psutil.cpu_count(logical=True)
        info["cpu_pct"] = psutil.cpu_percent(interval=0.1)
    except ImportError:
        info["ram_total_mb"] = 64_000   # fallback: sistema conocido (64 GB)
        info["cpu_cores"] = os.cpu_count() or 8
        info["cpu_pct"] = 0.0

    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            parts = r.stdout.strip().split(",")
            info["vram_total_mb"] = int(parts[0].strip())
            info["vram_free_mb"] = int(parts[1].strip())
    except Exception:
        pass

    info["budgets"] = BUDGETS
    return info


def can_afford(subsystem: str) -> bool:
    """Retorna True si el subsistema puede arrancar sin superar su presupuesto."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        free_mb = vm.available // (1024 * 1024)
        budget = BUDGETS.get(subsystem, {}).get("ram_mb", 0)
        return free_mb >= budget
    except ImportError:
        return True  # sin psutil, optimista
