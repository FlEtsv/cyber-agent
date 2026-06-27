"""
Router de modelo: decide automáticamente si usar el modelo rápido o el potente.

Rápido  (default): cyberagent-original = Qwen3-Coder-30B-A3B MoE Q3_K_M
Potente (escalado): modelo denso 32B cuando la tarea requiere razonamiento profundo

Heurística de complejidad (sin llamadas extra al LLM):
  - Tarea simple / chat / consulta rápida → modelo rápido
  - Arquitectura de sistema / exploit complejo / análisis profundo → modelo potente
"""

import os, re

# Set CYBERAGENT_FAST_MODEL / CYBERAGENT_POWER_MODEL in .env to enable real two-model routing.
# If POWER_MODEL is unset (or same as FAST_MODEL) routing is a no-op — safe default.
FAST_MODEL  = os.environ.get("CYBERAGENT_FAST_MODEL",  "cyberagent-original")
POWER_MODEL = os.environ.get("CYBERAGENT_POWER_MODEL", FAST_MODEL)

# Patrones que indican tarea de alta complejidad
_COMPLEX_PATTERNS = [
    r"arquitectura (completa|de sistema|del proyecto)",
    r"diseña (todo|el sistema|la infraestructura|desde cero)",
    r"implementa (completo|todo|desde cero|el sistema)",
    r"(exploit|shellcode|rop chain|buffer overflow).{0,40}(completo|funcional|working)",
    r"análisis (profundo|completo|detallado) de",
    r"refactoriza (todo|el proyecto|completamente)",
    r"(escribe|crea|genera).{0,20}(framework|sistema completo|librería completa)",
    r"investiga (todo|a fondo|en profundidad)",
    r"plan (detallado|completo|paso a paso).{0,30}(para|de)",
    r"auditor[iÃ­]a (extensa|meticulosa|profunda|completa)",
    r"(threat model|modelo de amenazas|razonamiento profundo)",
]

_COMPLEX_RE = re.compile("|".join(_COMPLEX_PATTERNS), re.IGNORECASE)
_EXTRA_COMPLEX_PATTERNS = [
    r"disena (todo|el sistema|la infraestructura|desde cero)",
    r"diseña (todo|el sistema|la infraestructura|desde cero)",
    r"auditoria (extensa|meticulosa|profunda|completa)",
    r"auditoría (extensa|meticulosa|profunda|completa)",
    r"autenticacion completo desde cero",
    r"autenticación completo desde cero",
]
_EXTRA_COMPLEX_RE = re.compile("|".join(_EXTRA_COMPLEX_PATTERNS), re.IGNORECASE)

# Palabras simples que fuerzan el modelo rápido independientemente del resto
_FAST_KEYWORDS = {
    "hola", "gracias", "ok", "bien", "sí", "no", "qué tal",
    "¿cuánto", "¿qué", "¿cómo estás", "lista", "muéstrame",
    "ram", "cpu", "procesos", "gpu", "disco", "ip",
}


def score_complexity(message: str) -> float:
    """Devuelve un score 0.0 (trivial) – 1.0 (muy complejo)."""
    msg = message.strip()
    lower = msg.lower()

    # Fuerza rápido para mensajes muy cortos o keywords simples
    if len(msg.split()) <= 8:
        if any(k in lower for k in _FAST_KEYWORDS):
            return 0.0

    score = 0.0

    # Longitud del mensaje
    words = len(msg.split())
    score += min(words / 300, 0.35)

    # Patrones de complejidad alta
    if _COMPLEX_RE.search(msg) or _EXTRA_COMPLEX_RE.search(msg):
        score += 0.6

    # Bloques de código en el mensaje (contexto largo)
    if msg.count("```") >= 2:
        score += 0.2

    # Múltiples párrafos = tarea multi-parte
    paragraphs = [p for p in msg.split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        score += 0.15

    return min(score, 1.0)


def route(message: str, threshold: float = 0.6) -> tuple[str, str]:
    """
    Devuelve (model_name, reason).
    threshold: score mínimo para escalar al modelo potente.
    """
    s = score_complexity(message)
    if s >= threshold:
        return POWER_MODEL, f"complejo: tarea compleja (score={s:.2f}) → modelo potente"
    return FAST_MODEL, f"tarea estándar (score={s:.2f}) → modelo rápido"
