"""
AC-05: Almacén de datasets de entrenamiento — jsonl comprimido, por modelo, versionado.

Los datasets se guardan como .jsonl.gz en la SD con versión y metadatos.
"""
from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

from app.storage.layout import layout


def save_dataset(
    model_id: str,
    samples: list[dict],
    version: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    AC-05: Guarda el dataset en formato jsonl.gz en la SD.

    Args:
        model_id: ID del modelo (ej: 'cyberagent-24b')
        samples: lista de muestras en formato chat JSONL
        version: versión (auto-generada si None)
        metadata: info adicional (hparams, fecha, n_samples, etc.)

    Returns:
        dict con 'ok', 'path', 'version', 'n_samples'
    """
    v = version or time.strftime("v%Y%m%d_%H%M%S")
    path = layout.dataset_path(model_id, v)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with gzip.open(path, "wt", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
            if metadata:
                f.write(json.dumps({"__meta__": True, **metadata}, ensure_ascii=False) + "\n")

        return {
            "ok": True,
            "path": str(path),
            "version": v,
            "n_samples": len(samples),
            "size_bytes": path.stat().st_size,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_dataset(model_id: str, version: str) -> list[dict]:
    """Carga un dataset versionado desde la SD."""
    path = layout.dataset_path(model_id, version)
    if not path.exists():
        return []
    samples = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if not d.get("__meta__"):
                    samples.append(d)
    except Exception:
        pass
    return samples


def list_versions(model_id: str) -> list[dict]:
    """Lista versiones disponibles para un modelo."""
    base = layout.datasets / model_id
    if not base.exists():
        return []
    versions = []
    for f in sorted(base.glob("*.jsonl.gz")):
        stat = f.stat()
        versions.append({
            "version": f.stem.replace(".jsonl", ""),
            "path": str(f),
            "size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
        })
    return versions
