"""
AB-02: Registro de fichas de modelos entrenables.

Fichas iniciales:
  - cyberagent-24b: el cerebro principal del agente (Mistral Nemo 24B)
  - codestral: especialista en código
  - vision-security: modelo de visión para detectar intrusos/gatos
  - tool-router: router de herramientas (elige qué herramienta usar)
"""
from __future__ import annotations

from app.training.model_card import ModelCard, card_to_dict

_REGISTRY: dict[str, ModelCard] = {}


def _register(card: ModelCard) -> None:
    _REGISTRY[card.id] = card


# ── Fichas registradas (AB-02) ─────────────────────────────────────────────────

_register(ModelCard(
    id="cyberagent-24b",
    base="mistral-nemo-24b",
    quant_train="Q4_K_M",
    destination="local",
    threshold=500,
    criticality="high",
    usage="Cerebro principal del agente — responde preguntas, razona, coordina herramientas",
    data_sources=["interaction", "feedback", "correction"],
    hparams_id="cyberagent-24b",
    system_prompt_template="",
))

_register(ModelCard(
    id="codestral",
    base="codestral-22b",
    quant_train="Q4_K_M",
    destination="local",
    threshold=300,
    criticality="medium",
    usage="Especialista en código — escribe, depura y refactoriza",
    data_sources=["interaction"],
    hparams_id="codestral",
))

_register(ModelCard(
    id="vision-security",
    base="llava:7b",
    quant_train="Q4_K_M",
    destination="local",
    threshold=200,
    criticality="high",
    usage="Análisis de imágenes de cámaras — detecta intrusos, gatos, anomalías",
    data_sources=["security", "feedback"],
    hparams_id="vision-security",
))

_register(ModelCard(
    id="tool-router",
    base="mistral-7b",
    quant_train="Q4_K_M",
    destination="runpod",
    threshold=1000,
    criticality="medium",
    usage="Router de herramientas — decide qué tool usar dado el intent del usuario",
    data_sources=["approval", "feedback"],
    hparams_id="tool-router",
))


# ── API ────────────────────────────────────────────────────────────────────────

def get(model_id: str) -> ModelCard | None:
    return _REGISTRY.get(model_id)


def all_cards() -> list[dict]:
    return [card_to_dict(c) for c in _REGISTRY.values()]


def all_ids() -> list[str]:
    return list(_REGISTRY.keys())
