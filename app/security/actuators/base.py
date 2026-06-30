"""
AT-01: Interfaz base para actuadores de disuasión.

Todos los actuadores implementan esta interfaz.
La capa de disuasión (AW) razona sobre la intención; el actuador
la traduce al HW disponible con degradación elegante (AT-03).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    PRESENCE   = "presence"   # Luz suave — marcar que hay alguien
    AUDIO_WARN = "audio_warn" # Sonido de aviso
    NARRATE    = "narrate"    # TTS narrando lo que ve la IA
    SIREN      = "siren"      # Sirena
    LIGHT      = "light"      # Luz potente
    DISCONNECT = "disconnect" # Desconectar/parar


@dataclass
class ActuatorCapabilities:
    intents: list[Intent]   # qué intenciones puede ejecutar
    max_volume_db: float = 85.0
    supports_tts: bool = False
    latency_ms: int = 500   # latencia estimada


class DeterrenceActuator(ABC):
    """AT-01: Interfaz base para todos los actuadores."""

    name: str = "base"
    capabilities: ActuatorCapabilities

    @abstractmethod
    def is_available(self) -> bool:
        """AT-04: ¿Está disponible este actuador ahora?"""
        ...

    @abstractmethod
    def fire(self, intent: Intent, payload: dict | None = None) -> bool:
        """
        Ejecutar una intención de disuasión.
        Retorna True si fue exitoso.
        payload: datos extra (texto para TTS, duración, etc.)
        """
        ...

    def supports(self, intent: Intent) -> bool:
        return intent in self.capabilities.intents

    def health(self) -> dict:
        return {"name": self.name, "available": self.is_available()}
