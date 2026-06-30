"""
AC-06: Anonimizar/limpiar PII sensible antes de entrenar.

Detecta y redacta:
  - Emails
  - Teléfonos
  - IPs privadas (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
  - Tokens API (strings de 32+ chars alfanuméricos)
  - Rutas absolutas del PC del usuario
"""
from __future__ import annotations

import re

_PATTERNS = [
    (re.compile(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b', re.I), '[EMAIL]'),
    (re.compile(r'\b(\+?\d[\d\s\-().]{7,}\d)\b'), '[PHONE]'),
    (re.compile(r'\b(192\.168\.\d{1,3}|10\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3})\.\d{1,3}\b'), '[IP_PRIV]'),
    (re.compile(r'\b[A-Za-z0-9_\-]{32,}\b'), '[TOKEN]'),
    (re.compile(r'[A-Z]:\\Users\\[^\\]+\\', re.I), '[USER_PATH]\\'),
    (re.compile(r'/home/[^/]+/', re.I), '[USER_PATH]/'),
]


def sanitize(text: str) -> str:
    """Redacta PII en el texto dado."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def sanitize_sample(sample: dict) -> dict:
    """Sanitiza instruction y response de una muestra."""
    out = dict(sample)
    out["instruction"] = sanitize(sample.get("instruction") or "")
    out["response"] = sanitize(sample.get("response") or "")
    return out


def sanitize_samples(samples: list[dict]) -> list[dict]:
    return [sanitize_sample(s) for s in samples]
