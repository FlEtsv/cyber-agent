"""
V-02 + V-04 + V-08: Árbitro de GPU — coordina el uso entre el agente del usuario
y los módulos de seguridad (visión, VLM).

Regla principal: la inferencia del usuario NUNCA espera por seguridad.
Cuando el agente del usuario está ocupando la GPU, seguridad degrada a CPU o nube.

Modo "no molestar": cuando el usuario está en tarea pesada (juego, render),
el broker bloquea cualquier uso de GPU por parte de seguridad.
"""
from __future__ import annotations

import threading
import time
from enum import Enum


class GPUUser(str, Enum):
    IDLE        = "idle"
    AGENT       = "agent"          # inferencia del usuario (prioridad máxima)
    SECURITY    = "security"       # visión/VLM de seguridad
    GAME_MODE   = "game_mode"      # no molestar — bloquea seguridad


class _Broker:
    def __init__(self):
        self._lock        = threading.Lock()
        self._current     = GPUUser.IDLE
        self._agent_ts    = 0.0     # timestamp del último uso del agente
        self._no_disturb  = False   # V-08: modo no molestar

    # ── Estado ────────────────────────────────────────────────────────────────

    def current_user(self) -> GPUUser:
        with self._lock:
            return self._current

    def is_busy(self) -> bool:
        with self._lock:
            return self._current != GPUUser.IDLE

    def is_agent_using(self) -> bool:
        with self._lock:
            return self._current == GPUUser.AGENT

    def is_security_blocked(self) -> bool:
        """Retorna True si seguridad NO puede usar la GPU ahora."""
        with self._lock:
            return self._no_disturb or self._current == GPUUser.AGENT

    # ── Adquisición / liberación ───────────────────────────────────────────────

    def acquire_agent(self) -> bool:
        """El agente del usuario adquiere la GPU. Siempre tiene éxito."""
        with self._lock:
            self._current  = GPUUser.AGENT
            self._agent_ts = time.monotonic()
        return True

    def release_agent(self) -> None:
        with self._lock:
            if self._current == GPUUser.AGENT:
                self._current = GPUUser.IDLE

    def acquire_security(self, timeout: float = 0.0) -> bool:
        """
        Seguridad intenta adquirir la GPU.

        Args:
            timeout: segundos máximos de espera (0 = non-blocking)

        Returns:
            True si adquirió la GPU, False si está bloqueada
        """
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                if not self.is_security_blocked():
                    self._current = GPUUser.SECURITY
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def release_security(self) -> None:
        with self._lock:
            if self._current == GPUUser.SECURITY:
                self._current = GPUUser.IDLE

    # ── V-08: Modo no molestar ─────────────────────────────────────────────────

    def set_no_disturb(self, enabled: bool) -> None:
        """Activa/desactiva el modo no molestar (bloquea GPU para seguridad)."""
        with self._lock:
            self._no_disturb = enabled
            if enabled and self._current == GPUUser.SECURITY:
                self._current = GPUUser.IDLE  # expulsa a seguridad

    def is_no_disturb(self) -> bool:
        with self._lock:
            return self._no_disturb

    # ── Status ─────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        with self._lock:
            return {
                "current_user": self._current.value,
                "no_disturb": self._no_disturb,
                "security_blocked": self.is_security_blocked(),
            }


# Singleton global
_broker = _Broker()

# Public API
def acquire_agent() -> bool:         return _broker.acquire_agent()
def release_agent() -> None:         _broker.release_agent()
def acquire_security(timeout: float = 0.0) -> bool: return _broker.acquire_security(timeout)
def release_security() -> None:      _broker.release_security()
def is_security_blocked() -> bool:   return _broker.is_security_blocked()
def set_no_disturb(v: bool) -> None: _broker.set_no_disturb(v)
def is_no_disturb() -> bool:         return _broker.is_no_disturb()
def status() -> dict:                return _broker.status()
