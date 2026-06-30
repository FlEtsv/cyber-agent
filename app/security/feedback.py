"""
W-06: Feedback de seguridad — captura señales de si una detección fue correcta,
falso positivo o falso negativo. Las muestras van a training_store con kind='security'
para entrenar el modelo de visión/detección.
"""
from __future__ import annotations


def record_detection_feedback(
    event_description: str,
    model_decision: str,
    correct: bool,
    false_positive: bool = False,
    false_negative: bool = False,
    camera_id: int | None = None,
    zone: str | None = None,
) -> int:
    """
    Registra feedback sobre una detección de seguridad.

    Args:
        event_description: qué detectó el sistema (texto o clasificación)
        model_decision: la decisión que tomó el modelo (alerta/ignorar/etc.)
        correct: True si la detección fue correcta
        false_positive: True si fue una falsa alarma
        false_negative: True si no detectó algo que debería haber detectado
        camera_id: id de la cámara (para filtrar por cámara en training)
        zone: nombre de la zona de vigilancia
    """
    signal = 1.0 if correct else (-1.0 if false_positive or false_negative else 0.0)
    label = "CORRECTO" if correct else ("FALSO_POSITIVO" if false_positive else "FALSO_NEGATIVO")

    instruction = event_description.strip()
    if zone:
        instruction = f"[Zona: {zone}] {instruction}"
    if camera_id is not None:
        instruction = f"[Cámara #{camera_id}] {instruction}"

    response = f"{model_decision}\n# Feedback: {label}"

    meta: dict = {
        "correct": correct,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }
    if camera_id is not None:
        meta["camera_id"] = camera_id
    if zone:
        meta["zone"] = zone

    try:
        from app.training_store import record
        return record(
            kind="security",
            instruction=instruction,
            response=response,
            signal=signal,
            meta=meta,
        )
    except Exception:
        return 0
