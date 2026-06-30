"""
Z-03: Scheduler de cómputo — mueve lo NO urgente a CPU cuando la GPU está ocupada.

Si el GPU broker dice que la GPU está ocupada por el agente del usuario,
las tareas no urgentes (embeddings, batch processing) se redirigen al CPUPool.
"""
from __future__ import annotations

import concurrent.futures
import threading
from typing import Callable


class ComputeScheduler:
    """
    Decide dónde ejecutar cada tarea según la disponibilidad de GPU.

    schedule(fn, gpu_fn=None, urgent=False):
      - Si GPU libre y gpu_fn dado: ejecuta gpu_fn en GPU
      - Si GPU ocupada o no hay gpu_fn: ejecuta fn en CPU pool
      - Si urgent=True: ejecuta fn en CPU sin esperar GPU

    Retorna un Future.
    """

    def schedule(
        self,
        cpu_fn: Callable,
        gpu_fn: Callable | None = None,
        urgent: bool = False,
        pool_name: str = "embedding",
        *args,
        **kwargs,
    ) -> concurrent.futures.Future:
        from app.security.gpu_broker import is_security_blocked
        from app.compute import cpu_pool

        use_cpu = urgent or gpu_fn is None or is_security_blocked()

        if use_cpu:
            submit = {
                "motion": cpu_pool.submit_motion,
                "embedding": cpu_pool.submit_embedding,
                "whisper": cpu_pool.submit_whisper,
                "vlm": cpu_pool.submit_vlm_cpu,
            }.get(pool_name, cpu_pool.submit_embedding)
            return submit(cpu_fn, *args, **kwargs)
        else:
            # GPU disponible: ejecutar gpu_fn en thread (libera GIL)
            return cpu_pool._embedding_pool.submit(gpu_fn, *args, **kwargs)


# Singleton
_scheduler = ComputeScheduler()


def schedule(cpu_fn, gpu_fn=None, urgent=False, pool_name="embedding", *args, **kwargs):
    return _scheduler.schedule(cpu_fn, gpu_fn, urgent, pool_name, *args, **kwargs)
