"""
AO-04 + AQ-01..AQ-04: Buffer de mensajes BAJA/PERIÓDICA → resumen periódico.

- Acumula notificaciones de baja importancia
- Agrupa repetidas (mismo tipo, mismo origen) para no spamear
- Envía resumen cada N minutos o bajo demanda (/resumen)
- Resumen diario programado (AQ-04)
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class DigestEntry:
    title: str
    body: str
    source: str
    count: int = 1
    first_ts: float = field(default_factory=time.time)
    last_ts: float = field(default_factory=time.time)


class DigestBuffer:
    """
    AQ-01 + AQ-02: Buffer con dedup y agrupación de mensajes.

    La clave de dedup es (source, title_prefix). Si llega el mismo evento
    N veces, se actualiza el contador y el timestamp en lugar de añadir entradas.
    """

    def __init__(self, flush_interval_minutes: int = 30):
        self._entries: dict[str, DigestEntry] = {}
        self._lock = threading.Lock()
        self._flush_interval = flush_interval_minutes * 60
        self._last_flush = time.time()

    def add(self, title: str, body: str, source: str = "system"):
        key = f"{source}:{title[:40]}"
        with self._lock:
            if key in self._entries:
                self._entries[key].count += 1
                self._entries[key].body = body  # actualizar cuerpo al último
                self._entries[key].last_ts = time.time()
            else:
                self._entries[key] = DigestEntry(
                    title=title, body=body, source=source
                )

    def should_flush(self) -> bool:
        return (time.time() - self._last_flush) >= self._flush_interval

    def flush(self) -> str | None:
        """Genera el texto del resumen y vacía el buffer. None si está vacío."""
        with self._lock:
            if not self._entries:
                self._last_flush = time.time()
                return None
            lines = [f"📋 <b>Resumen</b> ({len(self._entries)} notificaciones):"]
            for entry in sorted(self._entries.values(), key=lambda e: -e.count):
                suffix = f" (×{entry.count})" if entry.count > 1 else ""
                lines.append(f"• <b>{entry.title}</b>{suffix}: {entry.body[:80]}")
            self._entries.clear()
            self._last_flush = time.time()
        return "\n".join(lines)

    def size(self) -> int:
        with self._lock:
            return len(self._entries)


# Instancia global del buffer
_buffer = DigestBuffer(flush_interval_minutes=30)


def add_to_digest(title: str, body: str, source: str = "system"):
    _buffer.add(title, body, source)


def get_digest_text() -> str | None:
    return _buffer.flush()


def digest_size() -> int:
    return _buffer.size()


def maybe_auto_flush() -> bool:
    """Llama esto periódicamente. Retorna True si envió el digest."""
    if not _buffer.should_flush():
        return False
    text = _buffer.flush()
    if not text:
        return False
    try:
        from app.comms.router import send_message
        send_message(
            title="Resumen periódico",
            body=text,
            level=1,  # INFO
            source="digest",
        )
        return True
    except Exception:
        return False
