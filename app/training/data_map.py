"""
AB-03: Mapeo de qué datos de training_store entrenan cada modelo.

chats (interaction, feedback, correction) → cyberagent-24b
code (interaction con kind=code_specialist) → codestral
detecciones (security, feedback kind=security) → vision-security
tool_router (approval) → tool-router
"""
from __future__ import annotations

# model_id → lista de (kind, min_signal) para filtrar training_store
DATA_MAP: dict[str, list[tuple[str, float]]] = {
    "cyberagent-24b": [
        ("interaction", 0.0),
        ("feedback", 0.5),       # solo feedback positivo
        ("correction", 0.0),     # todas las correcciones
    ],
    "codestral": [
        ("interaction", 0.0),    # filtrado por meta.model después
    ],
    "vision-security": [
        ("security", 0.0),
        ("feedback", 0.5),
        ("predictor_feedback", 0.0),  # AL-08: bucle auto-supervisado del predictor
    ],
    "tool-router": [
        ("approval", -2.0),      # todos (aprobados y rechazados tienen señal)
    ],
}


def get_sources(model_id: str) -> list[tuple[str, float]]:
    """Retorna las fuentes de datos para un modelo dado."""
    return DATA_MAP.get(model_id, [])


# AL-08: Dataset del predictor visual → entra en el sistema de entrenamiento
PREDICTOR_MODEL_ID = "vision-security"
PREDICTOR_THRESHOLD = 500  # ejemplos antes de considerar reentrenamiento

def register_predictor_feedback(prediction: str, actual: str, correct: bool, pet_id: str = ""):
    """AL-08: Registrar feedback auto-supervisado del predictor → training_store."""
    signal = 1.0 if correct else -1.0
    try:
        from app.training_store import record
        record(
            kind="predictor_feedback",
            instruction=f"Prediccion de movimiento para pet={pet_id}: {prediction}",
            response=actual,
            signal=signal,
            meta={"pet_id": pet_id, "correct": correct},
        )
    except Exception:
        pass
