"""
AF-02: Preflight checks antes de iniciar entrenamiento.

Verifica:
  1. VRAM libre suficiente
  2. Espacio en disco
  3. Dataset listo (umbral superado)
  4. Avisa a seguridad (degradar a nube/CPU)
"""
from __future__ import annotations

from pathlib import Path


def run(model_id: str) -> dict:
    """
    Ejecuta todos los checks de preflight.

    Returns:
        {"ok": bool, "checks": {check: {ok, detail}}, "errors": [str]}
    """
    checks: dict[str, dict] = {}
    errors: list[str] = []

    # Check 1: dataset listo
    from app.training.threshold_watcher import check as th_check
    status = th_check(model_id, notify=False)
    checks["dataset"] = {
        "ok": status.get("ready", False),
        "detail": f"{status.get('count', 0)}/{status.get('threshold', '?')} ejemplos",
    }
    if not status.get("ready"):
        errors.append(f"Dataset no listo: {checks['dataset']['detail']}")

    # Check 2: VRAM libre
    from app.training.estimate import estimate
    est = estimate(model_id, n_samples=status.get("count", 500))
    vram_needed = est.get("vram_train_gb", 999)
    vram_free = _get_free_vram_gb()
    vram_ok = vram_free >= vram_needed or est.get("destination") == "runpod"
    checks["vram"] = {
        "ok": vram_ok,
        "detail": f"Necesaria: {vram_needed}GB, Libre: {vram_free}GB",
    }
    if not vram_ok:
        errors.append(f"VRAM insuficiente: {vram_needed}GB necesarios, {vram_free}GB libres")

    # Check 3: espacio en disco
    disk_ok, disk_detail = _check_disk()
    checks["disk"] = {"ok": disk_ok, "detail": disk_detail}
    if not disk_ok:
        errors.append(f"Espacio en disco insuficiente: {disk_detail}")

    # Aviso a seguridad (no es bloqueante — informativo)
    try:
        from app.security.gpu_broker import is_security_blocked, set_no_disturb
        set_no_disturb(True)   # bloquear GPU para seguridad durante entrenamiento
        checks["security_notified"] = {"ok": True, "detail": "Seguridad notificada (GPU bloqueada)"}
    except Exception as e:
        checks["security_notified"] = {"ok": False, "detail": str(e)}

    ok = all(v["ok"] for k, v in checks.items() if k != "security_notified")
    return {"ok": ok, "checks": checks, "errors": errors, "estimate": est}


def _get_free_vram_gb() -> float:
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            return int(r.stdout.strip()) / 1024
    except Exception:
        pass
    return 0.0


def _check_disk(min_gb: float = 20.0) -> tuple[bool, str]:
    try:
        import shutil
        base = Path(__file__).parent.parent.parent
        usage = shutil.disk_usage(str(base))
        free_gb = usage.free / (1024 ** 3)
        ok = free_gb >= min_gb
        return ok, f"{free_gb:.1f}GB libres (mínimo {min_gb}GB)"
    except Exception as e:
        return True, f"no verificado: {e}"
