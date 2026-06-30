"""
Y-01: Estructura de la SD (1.8 TB) — rutas base para modelos, datasets, videos, backups.

Todas las rutas en el sistema de almacenamiento externo deben usar esta configuración.
La ruta base por defecto es la SD; configurable por variable de entorno.
"""
from __future__ import annotations

import os
from pathlib import Path

# Ruta base configurable: SD_ROOT (default: D:/ o la SD si está montada)
def get_sd_root() -> Path:
    env = os.environ.get("SD_ROOT", "")
    if env:
        return Path(env)
    # Detección automática de la SD en Windows
    for drive in ["D", "E", "F", "G"]:
        candidate = Path(f"{drive}:/cyberagent")
        if candidate.exists():
            return candidate
    # Fallback local
    return Path(__file__).parent.parent.parent / "storage"


class StorageLayout:
    """Y-01: Estructura de directorios en la SD."""

    def __init__(self, root: Path | None = None):
        self.root = root or get_sd_root()

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def adapters(self) -> Path:
        return self.models / "adapters"

    @property
    def merged(self) -> Path:
        return self.models / "merged"

    @property
    def datasets(self) -> Path:
        return self.root / "datasets"

    @property
    def videos(self) -> Path:
        return self.root / "videos"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    def ensure(self):
        """Crea todos los directorios si no existen."""
        for d in [self.models, self.adapters, self.merged,
                  self.datasets, self.videos, self.backups]:
            d.mkdir(parents=True, exist_ok=True)

    def model_adapter_path(self, model_id: str, version: str) -> Path:
        return self.adapters / model_id / version

    def merged_model_path(self, model_id: str, version: str) -> Path:
        return self.merged / f"{model_id}-{version}"

    def dataset_path(self, model_id: str, version: str) -> Path:
        return self.datasets / model_id / f"{version}.jsonl.gz"

    def video_path(self, cam_id: str) -> Path:
        return self.videos / cam_id

    def backup_path(self, name: str) -> Path:
        return self.backups / name

    def info(self) -> dict:
        """Y-05: Info de espacio disponible."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(str(self.root))
            return {
                "root": str(self.root),
                "total_gb": round(total / 1e9, 1),
                "used_gb": round(used / 1e9, 1),
                "free_gb": round(free / 1e9, 1),
                "free_pct": round(free / total * 100, 1) if total > 0 else 0,
            }
        except Exception:
            return {"root": str(self.root), "error": "disk_usage failed"}


# Instancia global
layout = StorageLayout()
