"""
Tool router: selecciona el subconjunto de tools relevante para el mensaje actual.

Estrategia en dos capas:
  1. LLM rápido (mismo modelo, contexto mínimo ~150 tokens, respuesta ~20 tokens).
     Elige categorías de herramientas sin guardrails.
  2. Fallback keyword (Python puro, 0 ms) si el LLM falla o tarda >8 s.
"""
from __future__ import annotations
import json, httpx

# ── Siempre incluidas (núcleo de ejecución) ──────────────────────────────────
_ALWAYS = frozenset({"shell", "read_file", "write_file", "run_python"})

# ── Categorías disponibles ────────────────────────────────────────────────────
CATEGORIES: dict[str, set[str]] = {
    "web":       {"web_search", "web_fetch", "http_request", "ssl_info",
                  "http_headers_check", "dir_bruteforce", "web_crawl"},
    "files":     {"list_directory", "search_files", "grep_files", "diff_files",
                  "hash_file", "file_metadata"},
    "system":    {"list_processes", "system_info", "memory_info", "gpu_info",
                  "network_info", "env_vars", "process_tree", "process_info",
                  "kill_process", "install_package", "uninstall_package"},
    "network":   {"port_scan", "dns_lookup", "whois_lookup", "traceroute",
                  "banner_grab", "ping_sweep", "arp_cache", "network_connections"},
    "forensics": {"strings_extract", "hex_dump", "file_entropy", "pe_info",
                  "file_metadata", "registry_query", "list_services",
                  "check_persistence"},
    "encode":    {"encode_decode"},
    "media":     {"screenshot_pc", "clipboard_read", "clipboard_write",
                  "windows_notify", "open_browser"},
    "rag":       {"rag_search", "rag_add"},
    "self":      {"list_self_files", "syntax_check", "restart_self"},
}

# ── Keywords fallback (sin LLM) ───────────────────────────────────────────────
_KW: dict[str, set[str]] = {
    "web":       {"buscar","search","web","http","url","internet","fetch","api",
                  "rest","curl","download","descargar","ssl","https","página",
                  "pagina","sitio","scrape","crawl","endpoint","request","petici"},
    "files":     {"archivo","file","directorio","directory","carpeta","folder",
                  "grep","diferencia","diff","hash","md5","sha","metadatos",
                  "listar","ls","ruta","path","extensi"},
    "system":    {"proceso","process","memoria","memory","ram","gpu","vram","cpu",
                  "sistema","system","instalar","install","paquete","package",
                  "matar","kill","rendimiento","performance","variable","env",
                  "pip","npm","conda","hardware","temperatura","disco","disk"},
    "network":   {"puerto","port","scan","nmap","red","network","ip","dns",
                  "whois","traceroute","ping","arp","escanear","conexiones",
                  "firewall","subred","subnet","host","gateway","socket"},
    "forensics": {"malware","virus","exploit","vulnerabilidad","vulnerability",
                  "registro","registry","servicio","service","persistencia",
                  "persistence","strings","hex","entropia","entropy","pe",
                  "ejecutable","exe","dll","anali","forense","forensic",
                  "reversing","reverse","binary","ransomware","trojan","backdoor"},
    "encode":    {"base64","encode","decode","codif","decodif","cifr","descifr",
                  "rot13","jwt","xor","aes","rsa"},
    "media":     {"pantalla","screenshot","captura","portapapeles","clipboard",
                  "notificaci","notification","navegador","browser","abrir"},
    "rag":       {"recuerda","remember","aprende","learn","conocimiento",
                  "knowledge","rag","guardar conocimiento"},
    "self":      {"código propio","tu código","modif","repair","mejora",
                  "automod","reparar","reinici","restart","source"},
}

# ── Índice nombre→schema ──────────────────────────────────────────────────────
_schema_index: dict[str, dict] | None = None
_schema_lock = __import__("threading").Lock()


def _get_index() -> dict[str, dict]:
    global _schema_index
    if _schema_index is not None:
        return _schema_index
    with _schema_lock:
        if _schema_index is None:
            from app.tools import TOOLS_SCHEMA
            _schema_index = {t["function"]["name"]: t for t in TOOLS_SCHEMA}
    return _schema_index


def _build_schema(names: set[str]) -> list[dict]:
    index = _get_index()
    from app.tools import TOOLS_SCHEMA
    if not names:
        return TOOLS_SCHEMA
    return [t for n, t in index.items() if n in names]


# ── Capa 1: LLM router ────────────────────────────────────────────────────────
_ROUTER_SYSTEM = (
    "Eres un selector de herramientas. Dado un mensaje, responde SOLO con los "
    "nombres de categorías necesarias separadas por coma, sin explicación.\n"
    f"Categorías disponibles: {', '.join(CATEGORIES.keys())}, todas\n"
    "Si el mensaje es ambiguo o necesitas todo, responde: todas"
)


def _llm_route(message: str, model: str, ollama_url: str) -> set[str] | None:
    """
    Llama al modelo con un prompt de 150 tokens para elegir categorías.
    Timeout 8s — si falla devuelve None para activar fallback keyword.
    """
    from app.agent_log import log, log_exception
    payload = {
        "model":    model,
        "messages": [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user",   "content": message[:500]},
        ],
        "stream":  False,
        "options": {"num_ctx": 512, "temperature": 0, "top_k": 1, "num_predict": 40},
    }
    try:
        t = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
        log("INFO", "tool_router", "LLM route call iniciado", {"model": model, "msg": message[:100]})
        r = httpx.post(ollama_url, json=payload, timeout=t)
        if r.status_code != 200:
            log("WARN", "tool_router", f"LLM route HTTP {r.status_code}", {"body": r.text[:200]})
            return None
        text = r.json().get("message", {}).get("content", "").lower().strip()
        log("INFO", "tool_router", "LLM route respuesta", {"raw": text})
    except Exception as e:
        log_exception("tool_router", f"LLM route falló: {e} — usando keyword fallback")
        return None

    if not text or "todas" in text or "all" in text:
        log("INFO", "tool_router", "LLM route → todas (schema completo)")
        return None  # → fallback devuelve schema completo

    selected: set[str] = set()
    for token in text.replace(";", ",").split(","):
        cat = token.strip().rstrip(".")
        if cat in CATEGORIES:
            selected |= CATEGORIES[cat]

    log("INFO", "tool_router", f"LLM route → {len(selected)} tools", {"tools": list(selected)[:20]})
    return selected if selected else None


# ── Capa 2: keyword fallback ──────────────────────────────────────────────────
def _keyword_route(message: str, history: list | None,
                   called_tools: set[str] | None) -> set[str] | None:
    text = message.lower()
    if history:
        for m in history[-6:]:
            if m.get("role") in ("user", "assistant"):
                text += " " + (m.get("content") or "").lower()

    selected: set[str] = set()
    matched = False
    for cat, kws in _KW.items():
        if any(kw in text for kw in kws):
            selected |= CATEGORIES[cat]
            matched = True

    if called_tools:
        for name in called_tools:
            selected.add(name)
            for cat, tools in CATEGORIES.items():
                if name in tools:
                    selected |= tools
                    matched = True

    return selected if matched else None  # None → schema completo


# ── API pública ───────────────────────────────────────────────────────────────
def route_tools(
    message: str,
    history: list | None = None,
    called_tools: set[str] | None = None,
    model: str | None = None,
    ollama_url: str | None = None,
    use_llm: bool = True,
) -> list[dict]:
    """
    Devuelve el subconjunto de TOOLS_SCHEMA para este mensaje.
    Siempre incluye shell, read_file, write_file, run_python.
    Sin match → schema completo.
    """
    from app.tools import TOOLS_SCHEMA

    names: set[str] | None = None

    # Capa 1: LLM
    if use_llm and model and ollama_url:
        names = _llm_route(message, model, ollama_url)

    # Capa 2: keywords (fallback o cuando use_llm=False)
    if names is None:
        names = _keyword_route(message, history, called_tools)

    # Schema completo si sin match
    if names is None:
        return TOOLS_SCHEMA

    names |= _ALWAYS
    return _build_schema(names)
