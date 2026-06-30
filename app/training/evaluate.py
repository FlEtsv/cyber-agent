"""
AG-01 + AG-02: Evaluación post-entrenamiento + comparativa A/B.

Evalúa el nuevo adapter contra el modelo activo en:
1. Holdout del dataset (eval split de dataset_builder)
2. Tareas canónicas por modelo (respuestas esperadas hardcodeadas)

Promueve el nuevo model SOLO si mejora en al menos IMPROVEMENT_THRESHOLD.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# Umbral de mejora para promoción automática (AG-02)
IMPROVEMENT_THRESHOLD = 0.02  # 2% de mejora en score


@dataclass
class EvalResult:
    model_id: str
    adapter_version: str
    holdout_score: float   # 0.0-1.0
    canonical_score: float # 0.0-1.0
    final_score: float     # promedio ponderado
    n_holdout: int
    n_canonical: int
    details: dict = field(default_factory=dict)


def evaluate(
    model_id: str,
    adapter_version: str,
    eval_samples: list[dict],
) -> EvalResult:
    """
    AG-01: Evalúa el adapter en las muestras de evaluación.

    Métricas:
    - Holdout: distribución de señal en el split de evaluación (alta señal = bueno)
    - Canónicas: respuestas hardcodeadas por modelo (smoke test)

    Args:
        model_id: ID del modelo a evaluar
        adapter_version: versión del adapter nuevo
        eval_samples: muestras del split de evaluación

    Returns:
        EvalResult con scores
    """
    holdout_score = _evaluate_holdout(eval_samples)
    canonical_score = _evaluate_canonical(model_id)

    final = holdout_score * 0.7 + canonical_score * 0.3

    return EvalResult(
        model_id=model_id,
        adapter_version=adapter_version,
        holdout_score=holdout_score,
        canonical_score=canonical_score,
        final_score=round(final, 4),
        n_holdout=len(eval_samples),
        n_canonical=len(_CANONICAL.get(model_id, [])),
        details={
            "holdout_weight": 0.7,
            "canonical_weight": 0.3,
        }
    )


def should_promote(new_result: EvalResult, baseline_score: float) -> bool:
    """
    AG-02: ¿Promover el nuevo adapter? Solo si mejora en al menos IMPROVEMENT_THRESHOLD.
    """
    return new_result.final_score >= baseline_score + IMPROVEMENT_THRESHOLD


def _evaluate_holdout(samples: list[dict]) -> float:
    """
    Score del holdout: fracción de muestras con señal positiva (weight >= 0.5).
    En producción esto sería inferencia real + comparación con respuesta esperada.
    Aquí usamos la señal almacenada como proxy (no requiere GPU).
    """
    if not samples:
        return 0.5
    positive = sum(1 for s in samples if float(s.get("weight", 0.5)) >= 0.5)
    return positive / len(samples)


# Tareas canónicas por modelo — smoke test sin inferencia real
_CANONICAL: dict[str, list[dict]] = {
    "cyberagent-24b": [
        {"prompt": "¿Cuál es la capital de España?", "expected_contains": "Madrid"},
        {"prompt": "Suma 2+2", "expected_contains": "4"},
    ],
    "codestral": [
        {"prompt": "Escribe una función Python que sume dos números", "expected_contains": "def"},
    ],
}


def _evaluate_canonical(model_id: str) -> float:
    """
    AG-01: Evaluar tareas canónicas.
    Sin inferencia real (stub): devuelve 1.0 si hay tareas definidas, 0.5 si no.
    En producción: llamar a Ollama con el nuevo adapter y verificar respuestas.
    """
    tasks = _CANONICAL.get(model_id, [])
    if not tasks:
        return 0.5  # sin tareas → score neutro
    # Stub: score 0.8 (asumimos que el modelo básico pasa los tests)
    return 0.8
