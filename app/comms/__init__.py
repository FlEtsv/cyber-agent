"""
U-01: Módulo central de comunicaciones de CyberAgent.

Canal saliente único: Telegram. Todos los subsistemas (seguridad, agente,
supervisor, errores) usan este módulo en lugar de llamar directamente a
app.security.notify. El módulo de seguridad solo lo IMPORTA aquí.
"""
from app.comms.router import send_message, available

__all__ = ["send_message", "available"]
