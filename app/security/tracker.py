"""
AK-01 + AK-02: Tracker multi-objeto — enlaza detecciones entre frames y mantiene trayectorias.

Implementación simple tipo SORT (Simple Online and Realtime Tracking) usando
distancia IoU entre bboxes para asociar detecciones con tracks existentes.
No depende de scipy/lap — usa algoritmo greedy que funciona bien para N < 20 objetos.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Track:
    track_id: int
    label: str           # 'cat', 'person', etc.
    pet_id: int | None   # None si no re-identificado aún
    pet_name: str        # nombre o 'Desconocido'

    bbox: tuple[float, float, float, float]  # x1,y1,x2,y2 normalized
    confidence: float
    crop_b64: str

    first_seen: float    # timestamp unix
    last_seen: float
    age: int             # frames vivo
    hits: int            # detecciones confirmadas
    misses: int          # frames sin detección (prediction mode)

    positions: list[tuple[float, float, float]] = field(default_factory=list)
    # cada posición: (cx, cy, timestamp)

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def update(self, bbox, confidence, crop_b64, pet_id=None, pet_name="Desconocido"):
        self.bbox = bbox
        self.confidence = confidence
        self.crop_b64 = crop_b64
        if pet_id is not None:
            self.pet_id = pet_id
            self.pet_name = pet_name
        self.last_seen = time.time()
        self.age += 1
        self.hits += 1
        self.misses = 0
        cx, cy = self.centroid
        self.positions.append((cx, cy, self.last_seen))
        if len(self.positions) > 500:
            self.positions = self.positions[-500:]

    def predict(self):
        """Predice posición si no hay detección (mantiene última bbox)."""
        self.misses += 1
        self.age += 1


class MultiObjectTracker:
    """
    AK-01: Tracker multi-objeto ligero.

    Asociación greedy por IoU: cada detección nueva se asigna al track más cercano
    (IoU > min_iou). Tracks sin detección durante max_misses frames se eliminan.
    """

    def __init__(
        self,
        min_iou: float = 0.3,
        max_misses: int = 5,
        min_hits: int = 1,
    ):
        self.min_iou = min_iou
        self.max_misses = max_misses
        self.min_hits = min_hits
        self._tracks: dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: list[dict]) -> list[Track]:
        """
        AK-01: Actualiza el tracker con las detecciones del frame actual.

        Args:
            detections: lista de dicts con keys: label, confidence, bbox, crop_b64,
                        y opcionalmente pet_id, pet_name

        Returns:
            lista de tracks activos (hits >= min_hits, misses <= max_misses)
        """
        now = time.time()
        unmatched_dets = list(range(len(detections)))
        matched_tracks: set[int] = set()

        # Asociar detecciones con tracks existentes (greedy por IoU)
        for tid, track in list(self._tracks.items()):
            if not unmatched_dets:
                break
            best_iou = self.min_iou
            best_det_idx = None
            for i in unmatched_dets:
                iou = _iou(track.bbox, detections[i]["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_det_idx = i
            if best_det_idx is not None:
                d = detections[best_det_idx]
                track.update(
                    bbox=d["bbox"],
                    confidence=d["confidence"],
                    crop_b64=d.get("crop_b64", ""),
                    pet_id=d.get("pet_id"),
                    pet_name=d.get("pet_name", "Desconocido"),
                )
                matched_tracks.add(tid)
                unmatched_dets.remove(best_det_idx)
            else:
                track.predict()

        # Crear nuevos tracks para detecciones sin asignar
        for i in unmatched_dets:
            d = detections[i]
            track = Track(
                track_id=self._next_id,
                label=d.get("label", "unknown"),
                pet_id=d.get("pet_id"),
                pet_name=d.get("pet_name", "Desconocido"),
                bbox=d["bbox"],
                confidence=d["confidence"],
                crop_b64=d.get("crop_b64", ""),
                first_seen=now,
                last_seen=now,
                age=1,
                hits=1,
                misses=0,
            )
            cx, cy = track.centroid
            track.positions.append((cx, cy, now))
            self._tracks[self._next_id] = track
            self._next_id += 1

        # Eliminar tracks perdidos
        dead = [tid for tid, t in self._tracks.items() if t.misses > self.max_misses]
        for tid in dead:
            del self._tracks[tid]

        return [t for t in self._tracks.values() if t.hits >= self.min_hits]

    def active_tracks(self) -> list[Track]:
        return [t for t in self._tracks.values() if t.hits >= self.min_hits]

    def get_track(self, track_id: int) -> Track | None:
        return self._tracks.get(track_id)

    def stats(self) -> dict:
        active = self.active_tracks()
        return {
            "total_tracks": len(self._tracks),
            "active": len(active),
            "by_label": {
                label: sum(1 for t in active if t.label == label)
                for label in set(t.label for t in active)
            },
        }


def _iou(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


# Instancia global por cámara (crear una por cam_id)
def make_tracker(cam_id: str = "default") -> MultiObjectTracker:
    return MultiObjectTracker()
