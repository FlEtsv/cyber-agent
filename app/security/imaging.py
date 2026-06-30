"""
R-03: Mejora de imagen para capturar detalles importantes.

Operaciones disponibles:
- sharpen: nitidez para texto/matrículas
- denoise: reducir ruido en condiciones de poca luz
- enhance_contrast: mejorar contraste en imágenes oscuras
- crop_person: recortar/enfocar en una persona detectada
- enhance_face: mejorar resolución del área facial

Usa cv2 si está disponible; fallback a PIL/Pillow.
"""
from __future__ import annotations

import base64
import io
import logging

logger = logging.getLogger(__name__)


def enhance(image_b64: str, operation: str = "sharpen") -> str:
    """
    R-03: Aplica una operación de mejora a la imagen.

    Args:
        image_b64: imagen en base64
        operation: 'sharpen' | 'denoise' | 'enhance_contrast' | 'normalize'

    Returns:
        imagen mejorada en base64 (o la original si falla)
    """
    try:
        img_bytes = base64.b64decode(image_b64)
        result = _apply_cv2(img_bytes, operation)
        if result:
            return base64.b64encode(result).decode()
        result = _apply_pil(img_bytes, operation)
        if result:
            return base64.b64encode(result).decode()
    except Exception as e:
        logger.warning("imaging.enhance: %s", e)
    return image_b64  # fallback: imagen original


def crop_region(image_b64: str, bbox: tuple[float, float, float, float]) -> str:
    """
    Recorta una región de la imagen (bbox en coordenadas relativas 0.0-1.0).
    """
    try:
        img_bytes = base64.b64decode(image_b64)
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        x1 = int(bbox[0] * w)
        y1 = int(bbox[1] * h)
        x2 = int(bbox[2] * w)
        y2 = int(bbox[3] * h)
        cropped = img.crop((x1, y1, x2, y2))
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=95)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        logger.warning("imaging.crop_region: %s", e)
        return image_b64


def _apply_cv2(img_bytes: bytes, operation: str) -> bytes | None:
    """Mejora con OpenCV."""
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        if operation == "sharpen":
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            img = cv2.filter2D(img, -1, kernel)
        elif operation == "denoise":
            img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        elif operation == "enhance_contrast":
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        elif operation == "normalize":
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)

        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        return buf.tobytes()
    except ImportError:
        return None
    except Exception as e:
        logger.warning("imaging._apply_cv2: %s", e)
        return None


def _apply_pil(img_bytes: bytes, operation: str) -> bytes | None:
    """Mejora con Pillow (fallback si no hay cv2)."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        img = Image.open(io.BytesIO(img_bytes))

        if operation == "sharpen":
            img = img.filter(ImageFilter.SHARPEN)
        elif operation == "enhance_contrast":
            img = ImageEnhance.Contrast(img).enhance(1.5)
        elif operation == "denoise":
            img = img.filter(ImageFilter.MedianFilter(size=3))
        elif operation == "normalize":
            img = ImageEnhance.Brightness(img).enhance(1.2)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()
    except ImportError:
        return None
    except Exception as e:
        logger.warning("imaging._apply_pil: %s", e)
        return None


def pipeline(image_b64: str, operations: list[str]) -> str:
    """
    Aplica una secuencia de operaciones de mejora.
    """
    result = image_b64
    for op in operations:
        result = enhance(result, op)
    return result
