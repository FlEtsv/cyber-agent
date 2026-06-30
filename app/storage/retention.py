"""
Y-04: Retención LEGAL de video — 15 días obligatorios, auto-borrado de lo más viejo.

Recorre la carpeta de videos y elimina archivos con más de MAX_DAYS días.
Se ejecuta periódicamente desde el supervisor.
"""
from __future__ import annotations

import time
from pathlib import Path

MAX_DAYS = 15
_SECS_PER_DAY = 86400


def cleanup(videos_root: Path, max_days: int = MAX_DAYS) -> dict:
    """
    Y-04: Elimina videos con más de max_days días de antigüedad.

    Args:
        videos_root: directorio raíz de videos (layout.videos)
        max_days: días de retención máxima

    Returns:
        dict con 'deleted', 'freed_bytes', 'errors'
    """
    cutoff = time.time() - max_days * _SECS_PER_DAY
    deleted = 0
    freed = 0
    errors: list[str] = []

    if not videos_root.exists():
        return {"deleted": 0, "freed_bytes": 0, "errors": []}

    for f in videos_root.rglob("*.mp4"):
        try:
            mtime = f.stat().st_mtime
            if mtime < cutoff:
                size = f.stat().st_size
                f.unlink()
                deleted += 1
                freed += size
        except Exception as e:
            errors.append(f"{f}: {e}")

    return {"deleted": deleted, "freed_bytes": freed, "errors": errors}


def status(videos_root: Path, max_days: int = MAX_DAYS) -> dict:
    """Cuántos archivos/bytes están próximos a expirar o ya expirados."""
    now = time.time()
    cutoff = now - max_days * _SECS_PER_DAY
    expiring_soon = 0
    expired = 0
    total_bytes = 0

    if not videos_root.exists():
        return {"expired": 0, "expiring_soon": 0, "total_bytes": 0}

    for f in videos_root.rglob("*.mp4"):
        try:
            mtime = f.stat().st_mtime
            size = f.stat().st_size
            total_bytes += size
            if mtime < cutoff:
                expired += 1
            elif mtime < cutoff + 2 * _SECS_PER_DAY:
                expiring_soon += 1
        except Exception:
            pass

    return {"expired": expired, "expiring_soon": expiring_soon, "total_bytes": total_bytes}
