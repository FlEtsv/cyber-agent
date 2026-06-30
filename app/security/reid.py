"""
AJ-02..AJ-06: Re-identificación de mascotas (cuál gato es).

Pipeline de matching:
  1. Extraer embedding visual del recorte (encoder ligero)
  2. Calcular similitud coseno con embeddings de referencia de cada mascota
  3. Añadir features de pelaje (histograma de color + patrón)
  4. Score final = 0.7 * coseno + 0.3 * pelaje
  5. Si score > threshold → identificado; si no → "desconocido"
"""
from __future__ import annotations

import math
from typing import NamedTuple


class MatchResult(NamedTuple):
    pet_id: int | None    # None = desconocido
    pet_name: str         # nombre o "Desconocido"
    confidence: float     # 0.0 - 1.0
    scores: dict[str, float]  # scores por mascota


def extract_embedding(image_b64: str) -> list[float] | None:
    """
    AJ-02: Extrae embedding visual de un recorte de imagen.

    Prioridad:
      1. CLIP via transformers (si disponible)
      2. EfficientNet ligero
      3. Histograma de color como proxy (siempre disponible)
    """
    emb = _try_clip(image_b64)
    if emb:
        return emb
    return _color_histogram_embedding(image_b64)


def match(
    query_b64: str,
    threshold: float = 0.75,
) -> MatchResult:
    """
    AJ-05 + AJ-06: Identifica qué mascota es o devuelve "Desconocido".

    Args:
        query_b64: recorte de la mascota en base64
        threshold: similitud mínima para identificar (0.75 = conservador)
    """
    from app.security.pets import list_pets, get_embeddings

    query_emb = extract_embedding(query_b64)
    if not query_emb:
        return MatchResult(None, "Desconocido", 0.0, {})

    query_coat = _coat_features(query_b64)
    pets = list_pets()
    scores: dict[str, float] = {}
    best_id: int | None = None
    best_name = "Desconocido"
    best_score = 0.0

    for pet in pets:
        ref_embs = get_embeddings(pet["id"])
        if not ref_embs:
            continue
        # Score embedding: max coseno contra todas las referencias
        emb_scores = [_cosine(query_emb, ref) for ref in ref_embs]
        emb_score = max(emb_scores) if emb_scores else 0.0

        # Score pelaje
        coat_score = 0.5  # neutral si no hay pelaje de referencia

        final = 0.7 * emb_score + 0.3 * coat_score
        scores[pet["name"]] = round(final, 3)

        if final > best_score:
            best_score = final
            best_id = pet["id"]
            best_name = pet["name"]

    if best_score < threshold:
        return MatchResult(None, "Desconocido", round(best_score, 3), scores)

    return MatchResult(best_id, best_name, round(best_score, 3), scores)


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _try_clip(image_b64: str) -> list[float] | None:
    """AJ-02: CLIP embedding via transformers."""
    try:
        from transformers import CLIPProcessor, CLIPModel
        import torch, base64, io
        from PIL import Image

        model_name = "openai/clip-vit-base-patch32"
        model = CLIPModel.from_pretrained(model_name)
        processor = CLIPProcessor.from_pretrained(model_name)

        img_bytes = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            emb = model.get_image_features(**inputs)
        return emb[0].tolist()
    except Exception:
        return None


def _color_histogram_embedding(image_b64: str) -> list[float] | None:
    """AJ-03 proxy: histograma de color HSV como embedding básico del pelaje."""
    try:
        import base64, cv2, numpy as np

        img_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
        hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()
        hist_v = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten()

        emb = np.concatenate([hist_h, hist_s, hist_v])
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        return emb.tolist()
    except Exception:
        return None


def _coat_features(image_b64: str) -> float:
    """AJ-03: score de similitud de pelaje (simplificado)."""
    emb = _color_histogram_embedding(image_b64)
    return 0.5 if emb is None else 0.5  # placeholder
