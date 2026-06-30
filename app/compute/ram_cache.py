"""
Z-04: Caché en RAM de frames y embeddings (aprovecha los 64 GB del sistema).

Implementa un LRU + TTL cache en memoria para:
  - Frames de cámara recientes (evita reprocesar el mismo frame)
  - Embeddings RAG (costosos de calcular)
  - Snapshots de HA (reducir llamadas a la API)

Max size configurable; por defecto 2 GB de RAM.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Any


_DEFAULT_MAX_BYTES = 512 * 1024 * 1024  # 512 MB por defecto (se puede subir a 2 GB)
_DEFAULT_TTL = 300.0                     # 5 minutos


class RamCache:
    """LRU cache con límite de tamaño y TTL."""

    def __init__(self, max_bytes: int = _DEFAULT_MAX_BYTES, ttl: float = _DEFAULT_TTL):
        self.max_bytes = max_bytes
        self.ttl = ttl
        self._store: OrderedDict[str, tuple[Any, float, int]] = OrderedDict()
        self._current_bytes = 0
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _size_of(self, value: Any) -> int:
        try:
            if isinstance(value, (bytes, bytearray)):
                return len(value)
            if isinstance(value, str):
                return len(value.encode())
            if isinstance(value, list):
                return sum(self._size_of(v) for v in value)
            return 128
        except Exception:
            return 128

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            value, expire_at, _ = self._store[key]
            if time.monotonic() > expire_at:
                self._evict(key)
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        size = self._size_of(value)
        expire_at = time.monotonic() + (ttl if ttl is not None else self.ttl)
        with self._lock:
            if key in self._store:
                _, _, old_size = self._store[key]
                self._current_bytes -= old_size
            self._store[key] = (value, expire_at, size)
            self._current_bytes += size
            self._store.move_to_end(key)
            # evict LRU hasta caber en max_bytes
            while self._current_bytes > self.max_bytes and self._store:
                oldest = next(iter(self._store))
                self._evict(oldest)

    def _evict(self, key: str) -> None:
        if key in self._store:
            _, _, size = self._store.pop(key)
            self._current_bytes = max(0, self._current_bytes - size)

    def delete(self, key: str) -> None:
        with self._lock:
            self._evict(key)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries": len(self._store),
                "bytes": self._current_bytes,
                "max_bytes": self.max_bytes,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total else 0.0,
            }


def _hash_key(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()[:32]


# ── Instancias por tipo ────────────────────────────────────────────────────────

frame_cache     = RamCache(max_bytes=256 * 1024 * 1024, ttl=30.0)   # frames ~256 MB, 30s TTL
embedding_cache = RamCache(max_bytes=512 * 1024 * 1024, ttl=3600.0) # embeddings ~512 MB, 1h
snapshot_cache  = RamCache(max_bytes=64 * 1024 * 1024, ttl=10.0)    # HA snapshots, 10s
