"""
Z-02 + Z-05: Pool de workers CPU para cargas no urgentes.

Cargas típicas:
  - Detección de movimiento (OpenCV)
  - Transcripción (whisper.cpp)
  - Embeddings RAG
  - VLM backup en CPU

Usa concurrent.futures.ProcessPoolExecutor o ThreadPoolExecutor según la carga.
Por defecto ThreadPool para compatibilidad; usa ProcessPool para visión si está disponible.
"""
from __future__ import annotations

import concurrent.futures
import threading
import os


_DEFAULT_WORKERS = min(4, (os.cpu_count() or 4) - 1)  # deja 1 núcleo libre


class CPUPool:
    """
    Pool de workers CPU con cola implícita y límite de workers.

    Uso:
        pool = CPUPool(max_workers=2)
        future = pool.submit(my_fn, arg1, arg2)
        result = future.result()
    """

    def __init__(self, max_workers: int = _DEFAULT_WORKERS, use_processes: bool = False):
        self._max = max_workers
        self._use_proc = use_processes
        self._lock = threading.Lock()
        self._pool: concurrent.futures.Executor | None = None

    def _get_pool(self) -> concurrent.futures.Executor:
        with self._lock:
            if self._pool is None:
                if self._use_proc:
                    self._pool = concurrent.futures.ProcessPoolExecutor(max_workers=self._max)
                else:
                    self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=self._max)
        return self._pool

    def submit(self, fn, *args, **kwargs) -> concurrent.futures.Future:
        return self._get_pool().submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            if self._pool:
                self._pool.shutdown(wait=wait)
                self._pool = None


# ── Pools compartidos por subsistema ──────────────────────────────────────────

_motion_pool    = CPUPool(max_workers=2)   # V-01: detección de movimiento
_embedding_pool = CPUPool(max_workers=2)   # RAG embeddings
_whisper_pool   = CPUPool(max_workers=1)   # transcripción (single-instance)
_vlm_cpu_pool   = CPUPool(max_workers=1)   # V-06 Z-06: VLM backup en CPU


def submit_motion(fn, *args, **kwargs) -> concurrent.futures.Future:
    return _motion_pool.submit(fn, *args, **kwargs)


def submit_embedding(fn, *args, **kwargs) -> concurrent.futures.Future:
    return _embedding_pool.submit(fn, *args, **kwargs)


def submit_whisper(fn, *args, **kwargs) -> concurrent.futures.Future:
    return _whisper_pool.submit(fn, *args, **kwargs)


def submit_vlm_cpu(fn, *args, **kwargs) -> concurrent.futures.Future:
    return _vlm_cpu_pool.submit(fn, *args, **kwargs)
