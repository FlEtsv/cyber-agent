"""
U-01: Adaptador Telegram para app/comms.

Thin wrapper alrededor de app.security.notify para que comms/ no duplique
la lógica de autenticación ni la gestión de secretos.
"""
from __future__ import annotations

from app.security.notify import available, send, notify, _cfg  # re-export

__all__ = ["available", "send", "notify", "_cfg"]
