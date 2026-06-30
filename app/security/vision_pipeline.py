"""
V-06: Pipeline de visión con backpressure y cola.

Evita saturar el sistema cuando llegan muchos frames con movimiento:
- Cola limitada (max_queue): descarta frames nuevos si la cola está llena
- Worker único: procesa un frame a la vez via vision_router
- Stats: cuenta frames procesados, descartados, latencia media
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Callable


class VisionPipeline:
    """
    Cola + worker para análisis de visión.

    Uso:
        pipe = VisionPipeline(on_result=my_callback)
        pipe.start()
        pipe.enqueue(frame_bytes, camera_id=1)
        pipe.stop()
    """

    def __init__(
        self,
        on_result: Callable[[dict], None],
        max_queue: int = 5,
        prompt: str = "¿Hay intrusos, personas o animales en la imagen?",
    ):
        self.on_result  = on_result
        self.max_queue  = max_queue
        self.prompt     = prompt
        self._q: queue.Queue = queue.Queue(maxsize=max_queue)
        self._stop      = threading.Event()
        self._thread    = None
        self._stats     = {"enqueued": 0, "dropped": 0, "processed": 0, "errors": 0}
        self._lock      = threading.Lock()

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def enqueue(self, frame_bytes: bytes, camera_id: int = 0, is_threat: bool = False) -> bool:
        """
        Añade un frame a la cola. Descarta si está llena (backpressure).

        Returns:
            True si el frame fue encolado, False si fue descartado
        """
        try:
            self._q.put_nowait({"frame": frame_bytes, "cam": camera_id, "threat": is_threat,
                                "ts": time.monotonic()})
            with self._lock:
                self._stats["enqueued"] += 1
            return True
        except queue.Full:
            with self._lock:
                self._stats["dropped"] += 1
            return False

    def _worker(self) -> None:
        from app.security.vision_router import route
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=1.0)
            except queue.Empty:
                continue
            t0 = time.monotonic()
            try:
                import base64
                img_b64 = base64.b64encode(item["frame"]).decode()
                result = route(img_b64, self.prompt, is_threat=item["threat"])
                result["camera_id"] = item["cam"]
                result["latency_ms"] = round((time.monotonic() - t0) * 1000)
                result["queue_lag_ms"] = round((t0 - item["ts"]) * 1000)
                try:
                    self.on_result(result)
                except Exception:
                    pass
                with self._lock:
                    self._stats["processed"] += 1
            except Exception:
                with self._lock:
                    self._stats["errors"] += 1
            finally:
                self._q.task_done()

    def stats(self) -> dict:
        with self._lock:
            return dict(self._stats)

    def qsize(self) -> int:
        return self._q.qsize()
