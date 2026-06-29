"""
Router de modelo: decide automáticamente si usar el modelo rápido o el potente.

Rápido  (default): cyberagent-24b = Mistral Small 24B Q4_K_M (denso, local, ~13-17 tok/s)
Potente (escalado): Mistral nube (Medium/Large) o Codestral para código, si hay API key

Heurística de complejidad (sin llamadas extra al LLM):
  - Tarea simple / chat / consulta rápida → modelo rápido
  - Arquitectura de sistema / exploit complejo / análisis profundo → modelo potente
"""

import os, re

# Set CYBERAGENT_FAST_MODEL / CYBERAGENT_POWER_MODEL in .env to enable real two-model routing.
# If POWER_MODEL is unset (or same as FAST_MODEL) routing is a no-op — safe default.
FAST_MODEL  = os.environ.get("CYBERAGENT_FAST_MODEL",  "cyberagent-24b")
POWER_MODEL = os.environ.get("CYBERAGENT_POWER_MODEL", FAST_MODEL)

# Modelo Mistral por defecto para escalado en la nube cuando esté disponible.
MISTRAL_MODEL = os.environ.get("CYBERAGENT_MISTRAL_MODEL", "mistral-small-latest")

# Si el usuario quiere que el auto-router escale a Mistral en tareas complejas
# (en vez de al modelo potente local). Por defecto sí, si hay API key.
PREFER_CLOUD_FOR_COMPLEX = os.environ.get(
    "CYBERAGENT_PREFER_CLOUD", "1"
).strip() not in ("0", "false", "no", "")

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

# Tareas que Mistral (nube, con guardrails) probablemente rechazaría por parecer
# ilegales/no éticas. Estas SE QUEDAN en local (modelos abliterados, uso autorizado):
# no tiene sentido escalarlas a la nube porque volverían rechazadas.
_CLOUD_SENSITIVE_PATTERNS = [
    r"\bexploit\b", r"shellcode", r"rop chain", r"buffer overflow", r"0\s?day", r"cve-\d",
    r"\bmalware\b", r"ransomware", r"troyano", r"trojan", r"\brootkit\b", r"backdoor",
    r"keylogger", r"\bstealer\b", r"\brat\b", r"\bworm\b", r"\bgusano\b",
    r"reverse shell", r"\bpayload\b", r"msfvenom", r"metasploit", r"meterpreter",
    r"\bcrack(ear)?\b", r"keygen", r"pirat", r"bypass.{0,20}(licencia|license|auth|antivirus|av|edr|waf|2fa|mfa|login)",
    r"phishing", r"suplant", r"\bdeface", r"\bddos\b", r"denegaci[oó]n de servicio",
    r"evad(e|ir|ing).{0,20}(antivirus|av|edr|defender|detecci)", r"ofusca.{0,10}(c[oó]digo|payload|malware)",
    r"crypter", r"\bobfuscat", r"robar.{0,20}(credencial|contrase|password|sesi[oó]n|cookie|token)",
    r"steal.{0,20}(credential|password|cookie|token|session)", r"exfiltra", r"exfiltrat",
    r"command and control", r"\bc2\b", r"persistencia.{0,20}(oculta|sigilosa|maliciosa)",
    r"escalad.{0,15}privilegi", r"privilege escalation", r"privesc",
]
_CLOUD_SENSITIVE_RE = re.compile("|".join(_CLOUD_SENSITIVE_PATTERNS), re.IGNORECASE)


def is_cloud_sensitive(message: str) -> bool:
    """True si la tarea probablemente choque con los guardrails de Mistral (→ quédate local)."""
    return bool(_CLOUD_SENSITIVE_RE.search(message or ""))

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

    En tareas complejas escala a Mistral (nube) si hay API key y está habilitado;
    si no, al modelo potente local.
    """
    s = score_complexity(message)
    if s >= threshold:
        # Tareas que Mistral rechazaría por guardrails → se quedan en local potente.
        if is_cloud_sensitive(message):
            return POWER_MODEL, (
                f"complejo y sensible (score={s:.2f}) → local potente "
                "(Mistral lo rechazaría por guardrails)"
            )
        if PREFER_CLOUD_FOR_COMPLEX:
            try:
                from app.brain import mistral_available
                if mistral_available():
                    return MISTRAL_MODEL, (
                        f"complejo (score={s:.2f}) → Mistral nube ({MISTRAL_MODEL})"
                    )
            except Exception:
                pass
        return POWER_MODEL, f"complejo: tarea compleja (score={s:.2f}) → modelo potente"
    return FAST_MODEL, f"tarea estándar (score={s:.2f}) → modelo rápido"
