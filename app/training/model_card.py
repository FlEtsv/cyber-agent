"""
AB-01: Esquema ModelCard — ficha de un modelo entrenable.

Cada modelo que CyberAgent puede entrenar tiene una ficha con:
  - Identificador y base
  - Cuantización para entrenamiento
  - Destino del entrenamiento (local/runpod)
  - Umbral de ejemplos para disparar entrenamiento
  - Plantilla de prompt del sistema
  - Criticidad (cuánto afecta al sistema si la nueva versión es peor)
  - Uso (qué hace este modelo)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ModelCard:
    id: str                              # identificador único (ej: "cyberagent-24b")
    base: str                            # modelo base (ej: "mistral-nemo-24b")
    quant_train: str                     # cuantización para entrenar (ej: "Q4_K_M")
    destination: Literal["local", "runpod"] = "local"
    threshold: int = 500                 # ejemplos mínimos antes de entrenar
    system_prompt_template: str = ""     # plantilla del prompt de sistema
    criticality: Literal["high", "medium", "low"] = "medium"
    usage: str = ""                      # descripción de uso
    data_sources: list[str] = field(default_factory=list)  # kinds de training_store
    hparams_id: str = ""                 # referencia a HParams en hparams.py
    active_version: str = ""            # versión actualmente en producción
    versions: list[dict] = field(default_factory=list)  # historial de versiones


def card_to_dict(card: ModelCard) -> dict:
    return {
        "id": card.id,
        "base": card.base,
        "quant_train": card.quant_train,
        "destination": card.destination,
        "threshold": card.threshold,
        "criticality": card.criticality,
        "usage": card.usage,
        "data_sources": card.data_sources,
        "hparams_id": card.hparams_id,
        "active_version": card.active_version,
        "versions": card.versions,
    }
