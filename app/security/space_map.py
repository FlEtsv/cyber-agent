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


def get_heatmap_data(pet_id: str | None = None) -> dict:
    """
    AL-09: Devuelve datos de heatmap para el frontend.

    Returns:
        points: list of {x, y, count} — posiciones normalizadas con peso
        schedules: list of {hour, intensity} — actividad por hora del día
        routes: list of {from_zone, to_zone, count} — rutas entre zonas
    """
    import time
    from app.security import events as ev

    # Recoger posiciones registradas en eventos de cat_detected
    all_events = ev.recent(n=200, event_type="cat_detected")
    if pet_id:
        all_events = [e for e in all_events if str(e.get("pet_id", "")) == str(pet_id)]

    # Puntos del heatmap
    point_map: dict[tuple, int] = {}
    hour_counts: dict[int, int] = {}
    for e in all_events:
        cx = e.get("cx") or e.get("x")
        cy = e.get("cy") or e.get("y")
        if cx is not None and cy is not None:
            gx = round(float(cx), 2)
            gy = round(float(cy), 2)
            point_map[(gx, gy)] = point_map.get((gx, gy), 0) + 1
        ts = e.get("ts", 0)
        if ts:
            hour = int(time.localtime(ts).tm_hour)
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

    points = [{"x": k[0], "y": k[1], "count": v} for k, v in point_map.items()]
    max_count = max((p["count"] for p in points), default=1)
    for p in points:
        p["intensity"] = round(p["count"] / max_count, 3)

    max_h = max(hour_counts.values(), default=1)
    schedules = [
        {"hour": h, "intensity": round(c / max_h, 3)}
        for h, c in sorted(hour_counts.items())
    ]

    # Rutas simples: zonas consecutivas
    routes: list[dict] = []

    return {"points": points, "schedules": schedules, "routes": routes}
