"""
AK-03 + AK-04: Mapa espacial de la habitación.

Convierte coordenadas de frame (bbox normalizado 0-1) a un espacio de habitación
más interpretable. Permite heatmaps de ocupación y rutas por gato.

Diseñado para funcionar sin calibración de homografía (modo básico: las coords del frame
ya son relativas a la habitación). Si se proveen puntos de calibración, aplica perspectiva real.
"""
from __future__ import annotations

import json
import threading
from collections import defaultdict
from pathlib import Path

_SPACE_DB = Path(__file__).parent.parent.parent / "data" / "space_maps.json"
_lock = threading.Lock()


def _load() -> dict:
    if _SPACE_DB.exists():
        try:
            return json.loads(_SPACE_DB.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict):
    _SPACE_DB.parent.mkdir(parents=True, exist_ok=True)
    _SPACE_DB.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class OccupancyGrid:
    """
    AK-04: Grid de ocupación (heatmap de dónde va cada gato).

    Divide el espacio en celdas NxN y acumula visitas de cada track/pet.
    """

    def __init__(self, rows: int = 10, cols: int = 10):
        self.rows = rows
        self.cols = cols
        # grid[pet_id][row][col] = count de frames en esa celda
        self._grids: dict[str, list[list[int]]] = {}

    def _key(self, pet_id: int | None, label: str) -> str:
        if pet_id is not None:
            return f"pet_{pet_id}"
        return f"label_{label}"

    def record(self, cx: float, cy: float, pet_id: int | None = None, label: str = "cat"):
        """Registra una posición normalizada (0-1) en el grid."""
        key = self._key(pet_id, label)
        if key not in self._grids:
            self._grids[key] = [[0] * self.cols for _ in range(self.rows)]
        row = min(int(cy * self.rows), self.rows - 1)
        col = min(int(cx * self.cols), self.cols - 1)
        self._grids[key][row][col] += 1

    def heatmap(self, pet_id: int | None = None, label: str = "cat") -> list[list[int]]:
        key = self._key(pet_id, label)
        return self._grids.get(key, [[0] * self.cols for _ in range(self.rows)])

    def top_zones(self, pet_id: int | None = None, label: str = "cat", n: int = 5) -> list[dict]:
        """Devuelve las N celdas más visitadas como (row, col, cx, cy, count)."""
        grid = self.heatmap(pet_id, label)
        cells = []
        for r in range(self.rows):
            for c in range(self.cols):
                if grid[r][c] > 0:
                    cx = (c + 0.5) / self.cols
                    cy = (r + 0.5) / self.rows
                    cells.append({"row": r, "col": c, "cx": cx, "cy": cy, "count": grid[r][c]})
        cells.sort(key=lambda x: -x["count"])
        return cells[:n]

    def to_dict(self) -> dict:
        return {"rows": self.rows, "cols": self.cols, "grids": self._grids}

    @classmethod
    def from_dict(cls, d: dict) -> "OccupancyGrid":
        g = cls(d.get("rows", 10), d.get("cols", 10))
        g._grids = d.get("grids", {})
        return g


def save_grid(cam_id: str, grid: OccupancyGrid):
    with _lock:
        data = _load()
        data[cam_id] = grid.to_dict()
        _save(data)


def load_grid(cam_id: str) -> OccupancyGrid:
    with _lock:
        data = _load()
    if cam_id in data:
        return OccupancyGrid.from_dict(data[cam_id])
    return OccupancyGrid()


def normalize_position(
    bbox: tuple[float, float, float, float],
    homography_matrix: list[list[float]] | None = None,
) -> tuple[float, float]:
    """
    AK-03: Convierte bbox a posición normalizada en el mapa de habitación.

    Sin homografía: usa el centroide inferior del bbox (pies del gato en suelo).
    Con homografía: aplica transformación de perspectiva.
    """
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2
    cy = y2  # pie del gato = borde inferior del bbox

    if homography_matrix:
        try:
            import numpy as np
            H = np.array(homography_matrix, dtype=np.float32)
            pt = np.array([[[cx, cy]]], dtype=np.float32)
            # Perspectiva manual (sin cv2 para no depender en import-time)
            h00, h01, h02 = H[0]
            h10, h11, h12 = H[1]
            h20, h21, h22 = H[2]
            w = h20 * cx + h21 * cy + h22
            if w != 0:
                cx = (h00 * cx + h01 * cy + h02) / w
                cy = (h10 * cx + h11 * cy + h12) / w
        except Exception:
            pass

    return (max(0.0, min(1.0, cx)), max(0.0, min(1.0, cy)))
