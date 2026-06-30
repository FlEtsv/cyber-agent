"""
AI-01..AI-04: Detector de animales (capa 1 del pipeline de visión).

Detecta gatos, personas y otros objetos en imágenes usando:
  1. YOLO (ultralytics) si está instalado — más rápido
  2. VLM ligero via Ollama como fallback

Retorna bounding boxes con clase y score.
Recorta el animal normalizado para re-ID (AI-04).
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Detection:
    label: str                   # 'cat', 'person', 'dog', 'bird', ...
    confidence: float            # 0.0 - 1.0
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 (normalized 0-1)
    crop_b64: str = ""           # AI-04: recorte del animal en base64


DetectionList = list[Detection]


def detect(
    image_b64: str,
    classes: list[str] | None = None,  # None = all, ['cat','person'] para filtrar
) -> DetectionList:
    """
    AI-01 + AI-02: Detecta objetos en una imagen.

    Args:
        image_b64: imagen en base64 (JPEG/PNG)
        classes: clases a detectar (None = todas)

    Returns:
        lista de Detection con bbox y crop
    """
    result = _try_yolo(image_b64, classes)
    if result is not None:
        return result
    return _try_vlm(image_b64, classes)


def _try_yolo(image_b64: str, classes: list[str] | None) -> DetectionList | None:
    """AI-01: YOLO via ultralytics si está disponible."""
    try:
        from ultralytics import YOLO
    except ImportError:
        return None

    import tempfile, os, cv2, numpy as np

    # Decodificar imagen
    img_bytes = base64.b64decode(image_b64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    h, w = img.shape[:2]
    model = YOLO("yolov8n.pt")  # modelo ligero; se descarga automáticamente
    results = model(img, verbose=False)

    detections = []
    for box in results[0].boxes:
        label = model.names[int(box.cls[0])]
        if classes and label not in classes:
            continue
        conf = float(box.conf[0])
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
        # Normalizar bbox
        bbox = (x1 / w, y1 / h, x2 / w, y2 / h)
        # AI-04: recorte
        crop = img[max(0, int(y1)):min(h, int(y2)), max(0, int(x1)):min(w, int(x2))]
        _, crop_enc = cv2.imencode(".jpg", crop)
        crop_b64 = base64.b64encode(crop_enc.tobytes()).decode()
        detections.append(Detection(label=label, confidence=conf, bbox=bbox, crop_b64=crop_b64))

    return detections


def _try_vlm(image_b64: str, classes: list[str] | None) -> DetectionList:
    """AI-01 fallback: usa VLM para detección básica (sin bbox preciso)."""
    import os, httpx, json
    targets = ", ".join(classes or ["cat", "person", "animal"])
    prompt = (
        f"List all {targets} you see in this image. "
        "For each, provide: label and approximate position (top-left/center/bottom-right). "
        "Respond in JSON: [{\"label\":\"cat\",\"position\":\"center\",\"confidence\":0.9}]. "
        "Only JSON, no explanation."
    )
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = os.environ.get("SECURITY_VLM_MODEL", "llava:7b")
    try:
        r = httpx.post(
            f"{url}/api/generate",
            json={"model": model, "prompt": prompt, "images": [image_b64], "stream": False},
            timeout=30,
        )
        if r.status_code != 200:
            return []
        text = r.json().get("response", "").strip()
        # Intentar parsear JSON
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            items = json.loads(text[start:end])
            detections = []
            for item in items:
                label = item.get("label", "unknown")
                if classes and label not in classes:
                    continue
                conf = float(item.get("confidence", 0.7))
                # Sin bbox preciso del VLM — usar bbox aproximado por posición
                pos = item.get("position", "center")
                bbox = _pos_to_bbox(pos)
                detections.append(Detection(label=label, confidence=conf, bbox=bbox))
            return detections
    except Exception:
        pass
    return []


def _pos_to_bbox(pos: str) -> tuple[float, float, float, float]:
    mapping = {
        "top-left": (0.0, 0.0, 0.4, 0.4),
        "top": (0.2, 0.0, 0.8, 0.4),
        "top-right": (0.6, 0.0, 1.0, 0.4),
        "left": (0.0, 0.2, 0.4, 0.8),
        "center": (0.25, 0.25, 0.75, 0.75),
        "right": (0.6, 0.2, 1.0, 0.8),
        "bottom-left": (0.0, 0.6, 0.4, 1.0),
        "bottom": (0.2, 0.6, 0.8, 1.0),
        "bottom-right": (0.6, 0.6, 1.0, 1.0),
    }
    return mapping.get(pos.lower(), (0.25, 0.25, 0.75, 0.75))
