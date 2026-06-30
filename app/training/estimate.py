"""
AB-05: Estimador de recursos/tiempo por modelo (VRAM train, horas RunPod, coste $).

Estimaciones aproximadas basadas en tamaño del modelo y parámetros QLoRA.
"""
from __future__ import annotations

from app.training.hparams import get as get_hparams


# Tamaños de VRAM aproximados por modelo base (en GB)
_VRAM_BASE = {
    "mistral-nemo-24b": 12.0,   # Q4_K_M ~12 GB
    "codestral-22b":    10.0,
    "llava:7b":          4.0,
    "mistral-7b":        4.0,
}

# Coste RunPod por hora según VRAM necesaria (estimación)
_RUNPOD_COST = {
    "A100_80GB": 1.89,   # $/h
    "A40":       0.75,
    "RTX4090":   0.44,
    "RTX3090":   0.29,
}


def estimate(model_id: str, n_samples: int = 500) -> dict:
    """
    Estima recursos y coste para entrenar un modelo con n_samples muestras.

    Returns:
        dict con vram_gb, hours_estimate, runpod_cost_usd, gpu_recommended
    """
    from app.training.registry import get as get_card
    card = get_card(model_id)
    if not card:
        return {"error": f"Modelo '{model_id}' no encontrado"}

    base_vram = _VRAM_BASE.get(card.base, 8.0)
    hp = get_hparams(model_id)

    # VRAM para entrenamiento: base * 1.5 (activaciones + gradientes LoRA)
    train_vram = base_vram * 1.5 + 2.0  # +2 GB overhead
    train_vram = round(train_vram, 1)

    # Tiempo estimado: ~1 min por 100 muestras en un A100
    steps = (n_samples * hp.epochs) / (hp.batch_size * hp.grad_accum)
    hours = steps * 0.5 / 3600  # ~0.5s/step en A100
    hours = max(0.5, round(hours, 2))

    # GPU recomendada según VRAM necesaria
    if train_vram <= 16:
        gpu = "RTX4090" if card.destination == "local" else "A40"
    elif train_vram <= 24:
        gpu = "RTX4090" if card.destination == "local" else "A40"
    else:
        gpu = "A100_80GB"

    cost_usd = round(hours * _RUNPOD_COST.get(gpu, 0.5), 2)

    return {
        "model_id": model_id,
        "n_samples": n_samples,
        "vram_train_gb": train_vram,
        "hours_estimate": hours,
        "gpu_recommended": gpu,
        "runpod_cost_usd": cost_usd,
        "destination": card.destination,
    }
