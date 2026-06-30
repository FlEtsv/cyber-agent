"""
AG-04 + Y-08: Backup del vault/DB en la SD (rotación).

Hace copias comprimidas de las bases de datos críticas con rotación (mantiene N backups).
"""
from __future__ import annotations

import gzip
import shutil
import time
from pathlib import Path

_MAX_BACKUPS = 7  # rotación semanal


def backup_db(src: Path, backups_dir: Path, max_keep: int = _MAX_BACKUPS) -> dict:
    """
    Crea un backup comprimido (gzip) de una base de datos SQLite.
    Rota los backups más antiguos si hay más de max_keep.

    Args:
        src: ruta a la base de datos
        backups_dir: directorio de backups
        max_keep: número máximo de backups a mantener

    Returns:
        dict con 'ok', 'path', 'size_bytes'
    """
    if not src.exists():
        return {"ok": False, "error": f"{src} no existe"}

    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = backups_dir / f"{src.stem}_{ts}.db.gz"

    try:
        with open(src, "rb") as f_in, gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        # Rotar backups viejos del mismo DB
        pattern = f"{src.stem}_*.db.gz"
        existing = sorted(backups_dir.glob(pattern))
        while len(existing) > max_keep:
            existing[0].unlink()
            existing.pop(0)

        return {"ok": True, "path": str(dest), "size_bytes": dest.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def backup_all(data_dir: Path, backups_dir: Path) -> list[dict]:
    """Hace backup de todos los .db en data_dir."""
    results = []
    for db in data_dir.glob("*.db"):
        result = backup_db(db, backups_dir / db.stem)
        result["db"] = db.name
        results.append(result)
    return results
