"""
AG-03: Versionado de adapters/modelos + rollback.

Mantiene un registro de versiones por modelo en data/training_runs/{model_id}/versions.json
Permite promover una versión o hacer rollback a la anterior.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _versions_path(model_id: str) -> Path:
    p = Path(__file__).parent.parent.parent / "data" / "training_runs" / model_id / "versions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(model_id: str) -> list[dict]:
    p = _versions_path(model_id)
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save(model_id: str, versions: list[dict]) -> None:
    p = _versions_path(model_id)
    p.parent.mkdir(parents=True, exist_ok=True)   # robusto ante cualquier ruta
    p.write_text(json.dumps(versions, indent=2, ensure_ascii=False))


def register_version(
    model_id: str,
    adapter_path: str,
    metrics: dict,
    run_id: int | None = None,
) -> dict:
    """Registra una nueva versión del adapter."""
    versions = _load(model_id)
    version_n = len(versions) + 1
    entry = {
        "version": version_n,
        "ts": datetime.now(timezone.utc).isoformat(),
        "adapter_path": adapter_path,
        "metrics": metrics,
        "run_id": run_id,
        "active": False,
    }
    versions.append(entry)
    _save(model_id, versions)
    return entry


def promote(model_id: str, version: int | None = None) -> dict:
    """
    Promueve una versión a activa. Si version=None, promueve la última.
    """
    versions = _load(model_id)
    if not versions:
        return {"ok": False, "error": "Sin versiones registradas"}

    target_n = version or versions[-1]["version"]
    target = next((v for v in versions if v["version"] == target_n), None)
    if not target:
        return {"ok": False, "error": f"Versión {target_n} no encontrada"}

    # Desactivar todas
    for v in versions:
        v["active"] = False
    target["active"] = True
    _save(model_id, versions)

    return {"ok": True, "promoted_version": target_n, "metrics": target["metrics"]}


def rollback(model_id: str) -> dict:
    """Rollback a la versión activa anterior."""
    versions = _load(model_id)
    active_idx = next((i for i, v in enumerate(versions) if v.get("active")), -1)
    if active_idx <= 0:
        return {"ok": False, "error": "Sin versión anterior para rollback"}

    versions[active_idx]["active"] = False
    versions[active_idx - 1]["active"] = True
    _save(model_id, versions)
    return {"ok": True, "rolled_back_to": versions[active_idx - 1]["version"]}


def get_versions(model_id: str) -> list[dict]:
    return _load(model_id)


def get_active(model_id: str) -> dict | None:
    return next((v for v in _load(model_id) if v.get("active")), None)
