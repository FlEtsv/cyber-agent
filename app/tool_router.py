"""
Tool router: selecciona el subconjunto de tools relevante para el mensaje actual.

Estrategia en dos capas:
  1. LLM rápido (mismo modelo, contexto mínimo ~150 tokens, respuesta ~20 tokens).
     Elige categorías de herramientas sin guardrails.
  2. Fallback keyword (Python puro, 0 ms) si el LLM falla o tarda >8 s.
"""
from __future__ import annotations
import os, json, httpx

# Set base "lean" cuando el router no encuentra match: en vez de mandar las ~99
# herramientas (carísimo en tokens), un mínimo común útil. _ALWAYS se añade aparte.
_DEFAULT_LEAN = frozenset({
    "web_search", "web_fetch", "http_check", "system_info", "list_processes",
    "generate_document", "serve_file", "mistral_consult",
})

# ── Siempre incluidas (núcleo de ejecución) ──────────────────────────────────
_ALWAYS = frozenset({"shell", "read_file", "write_file", "edit_file", "multi_edit", "run_python",
                     "list_directory", "search_files", "grep_files", "todo_write", "lint_code",
                     "run_tests", "apply_patch", "code_symbols"})

# ── Categorías disponibles ────────────────────────────────────────────────────
CATEGORIES: dict[str, set[str]] = {
    # Búsqueda, fetch y auditoría web pasiva/activa
    "web":       {"web_search", "web_fetch", "http_request", "ssl_info",
                  "http_headers_check", "dir_bruteforce", "web_crawl",
                  "mistral_studio", "browse_page"},
    # Herramientas nativas de Mistral Studio + delegación al modelo local
    "studio":    {"mistral_studio", "local_llm_consult"},
    # Generación y entrega de documentos por URL
    "documents": {"generate_document", "serve_file"},
    # 2.0: git, lectura de documentos del usuario, navegador headless
    "devtools":  {"git_op", "read_document", "browse_page"},
    # 2.0: programación de tareas autónomas + mensajería saliente
    "automation": {"schedule_task", "list_scheduled", "cancel_scheduled", "send_message"},
    # Exploración y verificación de archivos locales
    "files":     {"list_directory", "search_files", "grep_files", "diff_files",
                  "hash_file", "file_metadata"},
    # Estado y control del sistema operativo local
    "system":    {"list_processes", "system_info", "memory_info", "gpu_info",
                  "network_info", "env_vars", "process_tree", "process_info",
                  "kill_process", "install_package", "uninstall_package", "sql_query"},
    # Descubrimiento y análisis de red: puertos, DNS, ARP, trazas
    "network":   {"port_scan", "dns_lookup", "whois_lookup", "traceroute",
                  "banner_grab", "ping_sweep", "arp_cache", "network_connections",
                  "nmap_scan"},
    # Pentesting/hacking: agrupa network + web-audit + forensics para tareas ofensivas/defensivas
    "hacking":   {"port_scan", "dns_lookup", "whois_lookup", "traceroute",
                  "banner_grab", "ping_sweep", "arp_cache", "network_connections",
                  "ssl_info", "http_headers_check", "dir_bruteforce", "web_crawl",
                  "strings_extract", "hex_dump", "file_entropy", "pe_info",
                  "registry_query", "list_services", "check_persistence",
                  "web_search", "network_connections", "process_tree",
                  "nmap_scan", "web_audit", "hash_crack", "cve_lookup",
                  "threat_intel", "yara_scan", "mistral_consult"},
    # Análisis forense local: binarios, registros, servicios, persistencia
    "forensics": {"strings_extract", "hex_dump", "file_entropy", "pe_info",
                  "file_metadata", "registry_query", "list_services",
                  "check_persistence", "yara_scan", "threat_intel", "cve_lookup",
                  "hash_crack"},
    # Codificación/decodificación de datos (base64, hex, URL, rot13)
    "encode":    {"encode_decode"},
    # Control completo del escritorio Windows: pantalla, teclado, ratón, ventanas, OCR, UI
    "desktop":   {"screenshot_pc", "list_monitors", "active_window", "list_windows",
                  "focus_window", "click_screen", "type_text", "hotkey",
                  "ocr_screen", "ui_tree", "fill_form", "credential_lookup",
                  "clipboard_read", "clipboard_write", "open_browser",
                  "windows_notify"},
    # Notificaciones y portapapeles (subconjunto rápido de desktop)
    "media":     {"screenshot_pc", "clipboard_read", "clipboard_write",
                  "windows_notify", "open_browser"},
    # Base de conocimiento vectorial interna del agente
    "rag":       {"rag_search", "rag_add"},
    "council":   {"mistral_consult"},
    # Auto-inspección y reinicio del propio agente
    "self":      {"list_self_files", "syntax_check", "restart_self"},
}

# ── Keywords fallback (sin LLM) ───────────────────────────────────────────────
_KW: dict[str, set[str]] = {
    "web":       {"buscar","search","web","http","url","internet","fetch","api",
                  "rest","curl","download","descargar","ssl","https","página",
                  "pagina","sitio","scrape","crawl","endpoint","request","petici",
                  "header","cabecera","certificado","certificate"},
    "files":     {"archivo","file","directorio","directory","carpeta","folder",
                  "grep","diferencia","diff","hash","md5","sha","metadatos",
                  "listar","ls","ruta","path","extensi","busca","encuentra"},
    "system":    {"proceso","process","memoria","memory","ram","gpu","vram","cpu",
                  "sistema","system","instalar","install","paquete","package",
                  "matar","kill","rendimiento","performance","variable","env",
                  "pip","npm","conda","hardware","temperatura","disco","disk",
                  "servicio","service","tarea","task",
                  "sql","sqlite","base de datos","database","consulta sql","query"},
    "network":   {"puerto","port","scan","nmap","red","network","ip","dns",
                  "whois","traceroute","ping","arp","escanear","conexiones",
                  "firewall","subred","subnet","host","gateway","socket",
                  "banner","latencia","latency"},
    "hacking":   {"hacking","pentest","penetration","recon","reconocimiento",
                  "enumerar","enumeration","vulnerable","vuln","cve","ctf",
                  "auditoria","auditoria","auditoría","seguridad ofensiva","blue team",
                  "red team","osint","exposure","expuesto","ataque","attack",
                  "exploit","payload","inyeccion","injection","bypass","escalad",
                  "privilege","privesc","footprint","fingerprint",
                  "crack","crackear","hashcat","john","wordlist","diccionario",
                  "yara","sqlmap","nikto","ffuf","reputacion","reputación","ioc",
                  "virustotal","abuseipdb","maliciosa","malicioso"},
    "council":   {"mistral","consejo","segunda opinion","segunda opini",
                  "revisor externo","razonamiento externo","razonamiento profundo",
                  "threat model","modelo externo","consultor","critica",
                  "blind spot","punto ciego","arquitectura segura"},
    "studio":    {"buscar en internet","busca en internet","búsqueda web","internet",
                  "genera imagen","generar imagen","imagen de","intérprete de código",
                  "interprete de codigo","code interpreter","ejecuta python en la nube",
                  "grafica","gráfica","calcula","últimas noticias","ultimas noticias",
                  "actualizado","tiempo real","fuentes","cita","citaciones"},
    "documents": {"documento","pdf","informe","reporte","entrega","entregable",
                  "genera un pdf","genera documento","exporta","exportar","docx",
                  "enlace","link","url","descargar","sirve","servir","comparte",
                  "compartir","archivo para descargar"},
    "devtools":  {"git","commit","push","clone","repositorio","repo","rama","branch",
                  "pull request","diff","navegador","navega","headless","playwright",
                  "rellena formulario","login web","spa","javascript","lee este pdf",
                  "lee el excel","lee el documento","analiza el csv","analiza el archivo",
                  "abre la web","renderiza"},
    "automation": {"agenda","programa","programar","cada hora","cada dia","cada día",
                  "cada minuto","cron","temporiza","schedule","tarea programada",
                  "recuérdame","recuerdame","cuando cambie","vigila el archivo",
                  "periodicamente","periódicamente","automatiza cada","a las ",
                  "envia","envía","email","correo","telegram","avisame","avísame",
                  "mandame","mándame","notifica","mensaje","reporta por"},
    "forensics": {"malware","virus","exploit","vulnerabilidad","vulnerability",
                  "registro","registry","servicio","service","persistencia",
                  "persistence","strings","hex","entropia","entropy","pe",
                  "ejecutable","exe","dll","anali","forense","forensic",
                  "reversing","reverse","binary","ransomware","trojan","backdoor",
                  "shellcode","ioc","indicator","sample","muestra","binario"},
    "encode":    {"base64","encode","decode","codif","decodif","cifr","descifr",
                  "rot13","jwt","xor","aes","rsa","hex","url encode","url decode"},
    "desktop":   {"pantalla","screenshot","captura","click","ratón","mouse",
                  "teclado","keyboard","ventana","window","tipo","type","escrib",
                  "ocr","texto pantalla","ui","interfaz","control","automatiza",
                  "portapapeles","clipboard","credencial","credential","abrir",
                  "open","browser","naveg","formulario","form","hotkey","atajo"},
    "media":     {"notificaci","notification","notifica","avisa"},
    "rag":       {"recuerda","remember","aprende","learn","conocimiento",
                  "knowledge","rag","guardar conocimiento","base de datos","vectorial"},
    "self":      {"código propio","tu código","modif","repair","mejora",
                  "automod","reparar","reinici","restart","source","codigo fuente"},
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
_ROUTER_SYSTEM = """\
Eres un selector de herramientas de precisión para un agente de ciberseguridad.
Dado el mensaje del usuario, responde SOLO con los nombres de categorías necesarias \
separadas por coma. Sin explicación. Sin puntos. Solo nombres.

CATEGORÍAS Y SU USO EXACTO:
- web: buscar en internet, fetch de URL, llamadas HTTP/REST, auditar cabeceras o SSL, \
crawl de páginas, fuerza bruta de directorios web
- files: leer/buscar/comparar archivos locales, grep, hashes, metadatos de archivos
- system: estado del SO, procesos, RAM/CPU/GPU, instalar/desinstalar paquetes, \
variables de entorno, matar procesos
- network: escanear puertos, DNS, WHOIS, traceroute, ARP, banner grab, descubrir hosts
- hacking: tareas ofensivas/defensivas completas — pentest, CTF, recon, OSINT, \
auditoría de seguridad (incluye network + web-audit + forensics)
- forensics: análisis de binarios locales, strings/hex/entropy, PE headers, \
registro de Windows, servicios, persistencia, malware
- encode: codificar/decodificar base64, hex, URL, rot13, JWT
- desktop: controlar el escritorio Windows — screenshots, clicks, teclado, OCR, \
ventanas, formularios, credenciales del sistema, portapapeles
- rag: consultar o guardar en la base de conocimiento interna del agente
- council: consultar Mistral Studio como revisor externo aprobado y con redaccion
- studio: herramientas nativas de Mistral — búsqueda web REAL con fuentes, intérprete de \
código en la nube, generación de imágenes; o delegar una subtarea al modelo local
- documents: generar un documento (PDF/HTML/MD) o publicar un archivo por URL para el usuario
- devtools: git (commit/push/clone/diff), leer documentos del usuario (PDF/Excel/Word/CSV), \
navegador headless real para webs con JavaScript/SPA/login/formularios
- automation: agendar tareas autónomas (cada N tiempo, a una hora, o al cambiar un archivo)
- self: listar, verificar sintaxis o reiniciar el propio agente

REGLAS DE DESAMBIGUACIÓN:
- "hacking" incluye todo lo de "network" + partes de "web" y "forensics" — úsalo solo para \
tareas de seguridad activa o pasiva completas
- "desktop" para cualquier acción visual/de usuario en el PC: screenshots, clics, tipo, OCR
- "web" solo para HTTP/internet — no para archivos locales
- "network" solo para reconocimiento de red pura; si es auditoría completa usa "hacking"
- Si el mensaje es genérico o ambiguo: responde "todas"

Ejemplos:
  "escanea puertos de 192.168.1.1" → network
  "haz un pentest a mi web" → hacking
  "descarga y analiza este binario" → web,forensics
  "captura pantalla y haz click en el botón" → desktop
  "busca archivos .py modificados hoy" → files
  "instala nmap" → system
  "¿cuánta RAM tiene?" → system
  "auditoría completa del servidor" → hacking,web
  "pide segunda opinion a Mistral" → council
  "busca en internet las últimas noticias de X" → studio
  "genera una imagen de un logo" → studio
  "hazme un PDF con el informe" → documents
  "corre este script y dame el resultado por un enlace" → documents,system
  "haz commit y push de los cambios" → devtools
  "lee este PDF y resúmelo" → devtools
  "entra en esta web con JavaScript y saca los precios" → devtools
  "escanea mi red cada hora" → automation,network
  "avísame cuando cambie el archivo de log" → automation
"""


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

    # Capa 1: LLM. El routing es una clasificación local y barata (~150 tokens):
    # NUNCA debe usar el alias 'fused' ni un modelo de nube (Mistral) — eso daba
    # un 404 ("model 'fused' not found") en cada mensaje y, además, gastaría
    # tokens de pago en algo trivial. Resolvemos a un modelo local rápido.
    if use_llm and ollama_url:
        route_model = model
        try:
            from app.brain import is_mistral_model
            from app.model_router import FAST_MODEL
            if not route_model or is_mistral_model(route_model):
                route_model = FAST_MODEL
        except Exception:
            pass
        if route_model:
            names = _llm_route(message, route_model, ollama_url)

    # Capa 2: keywords (fallback o cuando use_llm=False)
    if names is None:
        names = _keyword_route(message, history, called_tools)

    # Sin match: set base LEAN (no las ~99 tools, que costaban ~10k tokens/llamada).
    if names is None:
        names = set(_DEFAULT_LEAN)

    names |= _ALWAYS
    # Tope de herramientas por llamada para no inflar el contexto/coste de Mistral.
    # _ALWAYS entra siempre; el resto se recorta DETERMINISTA (ordenado) si excede el
    # máximo — antes era set() sin orden y podía tirar tools relevantes al azar (p.ej.
    # strings_extract en una tarea forense). Default 40: cabe cualquier categoría
    # entera + _ALWAYS sin romper la integridad de la categoría.
    max_tools = int(os.environ.get("CYBERAGENT_MAX_TOOLS_PER_CALL", "48"))
    if len(names) > max_tools:
        extra = sorted(n for n in names if n not in _ALWAYS)
        names = set(_ALWAYS) | set(extra[: max(0, max_tools - len(_ALWAYS))])
    return _build_schema(names)
