"""
V-01: Detección de movimiento en CPU (OpenCV o ffmpeg).

Capa 0 del pipeline de visión: analiza frames en CPU sin GPU.
Solo activa el VLM (costoso) si hay movimiento real, ahorrando VRAM.

Gateado por SECURITY_ENABLED; siempre corre en CPU.
"""
from __future__ import annotations

import threading
from typing import Callable


def _has_cv2() -> bool:
    try:
        import cv2
        return True
    except ImportError:
        return False


def detect_motion_frame(
    prev_frame_gray,
    curr_frame_gray,
    threshold: float = 25.0,
    min_area: int = 500,
):
    """
    Compara dos frames en escala de grises y detecta movimiento.

    Returns:
        (has_motion: bool, motion_area: int, contours)
    """
    if not _has_cv2():
        return False, 0, []
    import cv2
    import numpy as np

    diff = cv2.absdiff(prev_frame_gray, curr_frame_gray)
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    total_area = 0
    significant = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area >= min_area:
            total_area += area
            significant.append(c)

    return bool(significant), total_area, significant


class MotionDetector:
    """
    Detecta movimiento en un flujo de frames (imágenes en bytes).
    Llama a `on_motion(frame_bytes)` cuando detecta movimiento real.

    No requiere GPU. Corre en el hilo del llamador.
    """

    def __init__(
        self,
        on_motion: Callable[[bytes], None],
        threshold: float = 25.0,
        min_area: int = 500,
        cooldown_frames: int = 10,
    ):
        self.on_motion      = on_motion
        self.threshold      = threshold
        self.min_area       = min_area
        self.cooldown_frames = cooldown_frames
        self._prev_gray     = None
        self._cooldown      = 0
        self._lock          = threading.Lock()

    def feed(self, frame_bytes: bytes) -> bool:
        """
        Procesa un frame. Retorna True si se detectó movimiento.

        Args:
            frame_bytes: JPEG/PNG en bytes
        """
        if not _has_cv2():
            return False
        import cv2
        import numpy as np

        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        with self._lock:
            if self._prev_gray is None:
                self._prev_gray = gray
                return False

            has_motion, area, _ = detect_motion_frame(
                self._prev_gray, gray, self.threshold, self.min_area
            )
            self._prev_gray = gray

            if self._cooldown > 0:
                self._cooldown -= 1
                return False

            if has_motion:
                self._cooldown = self.cooldown_frames
                try:
                    self.on_motion(frame_bytes)
                except Exception:
                    pass
                return True

        return False

    def reset(self) -> None:
        with self._lock:
            self._prev_gray = None
            self._cooldown = 0
