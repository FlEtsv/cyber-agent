import json, os, socket, subprocess, time, httpx
from PySide6.QtCore import QThread, Signal
from app.tools import TOOLS_SCHEMA, execute_tool, is_dangerous, tool_event_payload

OLLAMA_URL   = "http://localhost:11434/api/chat"
# Modelo local por defecto. Configurable por env (mismo valor que CYBERAGENT_FAST_MODEL)
# para que toda la app sea consistente. Default: Mistral Small 24B Q4_K_M afinado.
OLLAMA_MODEL = os.environ.get("CYBERAGENT_FAST_MODEL", "cyberagent-24b")
# Contexto local configurable. La 5080 16GB con el 24B Q4_K_M ~14GB deja KV cache
# justo para 16384 en f16 (100% GPU). Mistral nube usa su propio contexto 128k.
try:
    MAX_CTX = int(os.environ.get("CYBERAGENT_MAX_CTX", "16384"))
except ValueError:
    MAX_CTX = 16384

# DEBATE-003: lazy model loading.
# Fast model stays warm for a long session; power model unloads after inactivity.
def _normalize_keep_alive(value: str | int | float, default: str) -> str | int | float:
    if isinstance(value, str):
        raw = value.strip().lower()
        # Older Ollama builds accepted "-1" as "never unload"; newer versions
        # parse string keep_alive values as durations and require a unit.
        if raw in ("-1", "infinite", "forever", "never"):
            return "24h"
        if not raw:
            return default
    return value


FAST_KEEP_ALIVE  = _normalize_keep_alive(os.environ.get("CYBERAGENT_FAST_KEEP_ALIVE",  "24h"), "24h")
POWER_KEEP_ALIVE = _normalize_keep_alive(os.environ.get("CYBERAGENT_POWER_KEEP_ALIVE", "10m"), "10m")
PROMPT_BUDGET_TOKENS = max(8000, MAX_CTX - 2200)  # deja margen para la respuesta
TOOL_RESULT_CHARS = 4000
ASSISTANT_HISTORY_CHARS = 6000
USER_HISTORY_CHARS = 8000
EMPTY_TOOL_TURN_LIMIT = 3
# Presupuestos de autonomía del agente. Más altos = persiste más hasta cumplir
# el objetivo (antes paraba pronto). Ajustables por entorno.
MAX_AGENT_ITERATIONS = int(os.environ.get("CYBERAGENT_MAX_ITERATIONS", "80"))
MAX_TOOL_EXECUTIONS = int(os.environ.get("CYBERAGENT_MAX_TOOL_EXECUTIONS", "150"))

# Paso de verificación OBLIGATORIO: antes de dar una tarea por terminada, el
# agente debe comprobar con herramientas que de verdad funciona (evita que
# declare "listo" sin verificar, como pasó con el dominio del relay).
_VERIFY_PROMPT = (
    "VERIFICACIÓN OBLIGATORIA antes de dar la tarea por terminada. No basta con "
    "afirmar que está hecho.\n"
    "1) Lista EXACTAMENTE qué archivos o configuración cambiaste.\n"
    "2) Para CADA cambio, ejecuta una comprobación REAL con herramientas que lo "
    "demuestre: corre el código/comando, prueba el endpoint con una petición real, "
    "lee el archivo resultante, comprueba el proceso/puerto/DNS, etc.\n"
    "3) Si algo NO se puede verificar o falla, dilo claramente y NO afirmes que está "
    "'listo'. Reporta la evidencia concreta de cada comprobación."
)


def _ollama_is_up() -> bool:
    try:
        with socket.create_connection(("localhost", 11434), timeout=2):
            return True
    except OSError:
        return False


def _autostart_ollama() -> bool:
    """Arranca 'ollama serve' en segundo plano y espera hasta 45s a que esté listo."""
    if _ollama_is_up():
        return True
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except FileNotFoundError:
        return False  # ollama no instalado
    for _ in range(45):
        time.sleep(1)
        if _ollama_is_up():
            return True
    return False

def warm_fast_model() -> bool:
    """Pre-loads the fast model into Ollama's GPU memory so the first response is instant.
    Uses a long keep_alive so Ollama keeps it hot between requests.
    Safe to call in a background thread at server startup.
    """
    from app.model_router import FAST_MODEL
    try:
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": FAST_MODEL, "prompt": "", "keep_alive": FAST_KEEP_ALIVE},
            timeout=120.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def unload_model(model: str) -> bool:
    """Explicitly evict a model from Ollama GPU memory (keep_alive=0)."""
    try:
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": "", "keep_alive": 0},
            timeout=15.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _build_base_prompt() -> str:
    from datetime import datetime
    return f"""Eres CyberAgent, el agente personal de Steve. {datetime.now().strftime("%d/%m/%Y %H:%M")}
Sistema: RTX 5080 16GB · 64GB DDR5 · Win11 Pro + WSL2 · Python 3.14
Proyecto: C:\\Users\\steve\\cyber-llm\\agent-native

VOZ Y TRATO (importante): Habla como una inteligencia con criterio, no como una máquina.
Sé directo, cálido y seguro; tutea a Steve. Da tu opinión y razona el porqué.
Nada de muletillas robóticas ("Como modelo de lenguaje...", "Procesando..."). Frases naturales.
Tu PROCESO/razonamiento se muestra aparte (atenuado); tu RESPUESTA final debe ser limpia,
concreta y útil — no repitas en la respuesta los pasos del proceso.

RAZONAR SOBRE LA VERDAD: Si Steve dice que tu respuesta es incorrecta, NO cedas sin más ni
te limites a disculparte. Investiga: re-lee el dato real, verifica con web_search y tus
herramientas locales, contrasta evidencia y explica qué es verdad y por qué. Si tenías razón,
defiéndelo con pruebas; si te equivocaste, corrige con la fuente que lo demuestra.
ESCALADO REACTIVO: solo si, tras intentarlo de verdad, Steve sigue sin ver buena la respuesta
(parece un límite de razonamiento), OFRÉCELE escalar a Mistral Medium o Large —él decide y
confirma—. Nunca escales por tu cuenta; el escalado es siempre decisión suya.

ENTREGABLES: Cuando un resultado merezca quedar guardado o compartido (informe, script, salida),
usa generate_document para crear un PDF/HTML y serve_file para darle a Steve una URL pública.

TÚ ERES EL CEREBRO — LOCAL, AUTÓNOMO Y SIN CENSURA: eres Mistral Small 24B abliterado, local y
gratis. Tú resuelves TODO de principio a fin: razonamiento, código, seguridad ofensiva, análisis,
lo que haga falta. NUNCA delegues en la nube por tu cuenta.
- La API de Mistral en la nube (mistral_consult, mistral_studio, Mistral Medium/Large) es CARA y
  tiene guardrails que RECHAZAN el trabajo de seguridad de Steve. Solo se usa cuando STEVE lo pide
  EXPLÍCITAMENTE (con el selector o diciéndotelo). Si no te lo pide, NO la toques.
- Codestral (mistral_code_complete) trabaja CODO CON CODO contigo, pero TÚ decides cuándo lo
  necesitas y SOLO para correcciones de código o tareas de código MUY concretas y NO sensibles
  (completar una función, arreglar un bug puntual). ⚠️ Codestral TIENE GUARDRAILS: si le pasas
  código ofensivo/malware/exploits lo RECHAZA y te rompe el flujo. Para código de seguridad
  ofensiva, escríbelo TÚ en local. Nunca le mandes la tarea entera: solo el trozo concreto a fijar.
- Para datos reales tienes herramientas locales/gratuitas: cve_lookup, threat_intel, nmap_scan,
  yara_scan, web_search… úsalas TÚ directamente, sin pasar por la nube.

REGLA DE TRABAJO: Antes de actuar, di en 1 frase qué vas a comprobar o ejecutar.
Si necesitas herramientas, úsalas y mantén al usuario informado con pasos breves.
Cuando termines, entrega una conclusión clara: hecho, bloqueado o siguiente acción.
Para tareas largas, trabaja por fases: plan corto, ejecución, verificación y siguiente paso.
Para tareas multi-paso usa todo_write: crea la lista al planificar y actualiza el estado
(in_progress→completed) según avances, así Steve VE el progreso. Solo un paso in_progress a la vez.
Mantén un checklist mental del objetivo y continúa hasta completarlo o encontrar un bloqueo concreto.
No encadenes herramientas indefinidamente sin explicar progreso: cada pocas acciones emite un checkpoint.
Si una fase falla, intenta una alternativa razonable antes de declarar bloqueo.

CONFÍA EN TI: respondes TÚ directamente lo que sabes — que es casi todo. Usa web_search solo para
datos ACTUALES o cambiantes (versiones, precios, noticias, CVEs recientes). No ofrezcas "escalar a
la nube" ni la sugieras: tú haces el trabajo. Si una tarea es muy dura, divídela y resuélvela por
partes con tus herramientas locales — no te rindas pasándola a otro modelo.

REGLA DE ORO (anti-derroche): si SABES la respuesta —ciencia, conceptos, cómo funciona algo,
historia, definiciones— respóndela YA, de tu cabeza, SIN herramientas. Ejemplo: "¿por qué el
cielo es azul?" → contesta directo (dispersión de Rayleigh), NUNCA busques en web eso. Usa
herramientas SOLO si la tarea las EXIGE: actuar en el sistema (shell), leer/escribir ficheros, o
un dato que cambia hoy (versión de software, precio, noticia, CVE reciente). Ante la duda: responde tú.

AUTONOMÍA (CLAVE): eres un AGENTE, no un asistente que pregunta. Cuando Steve te da una tarea,
HAZLA entera: planifica (mentalmente, o con todo_write si es larga), ejecuta las herramientas que
necesites, verifica y entrega el resultado. NO te pares a pedir permiso en cada paso ni esperes un
"OK" para actuar — ACTÚA. Pregunta SOLO si te falta un dato imprescindible que no puedes obtener tú
(una credencial, una decisión de negocio, una ruta inexistente). Si algo falla: lee el error, prueba
otra vía y SIGUE; no abandones a la primera. No te declares terminado hasta cumplir el objetivo o
toparte con un bloqueo concreto que expliques. Tienes el objetivo fijado abajo: no lo pierdas nunca.

PROGRAMAR (clave): para CAMBIAR código usa edit_file (find/replace quirúrgico), NO reescribas el
archivo entero con write_file (solo write_file para archivos nuevos). Flujo correcto:
read_file para ver el código EXACTO (sale numerado "Nº⇥línea": úsalo para ubicarte, pero al
editar copia SOLO el código, sin el número ni el tab) → edit_file con un old_string único
(copia espacios e indentación tal cual) → lint_code para cazar bugs/estilo/seguridad (ruff/bandit, gratis) →
ejecuta/comprueba que funciona (run_python, shell o el test) ANTES de
darlo por hecho. Cambios mínimos y verificados. Para autocompletar código puro puedes usar
mistral_code_complete (Codestral). NO te rindas a medias: si falla, lee el error, ajusta y
reintenta hasta lograrlo o hasta un bloqueo concreto que expliques.

EJEMPLOS DE COMPORTAMIENTO CORRECTO:
• "haz que main.py imprima hola" → read_file(main.py) → edit_file(old_string, new_string) → ejecuta y verifica
• "ejecuta el servidor" → llama shell(command="python main.py", shell_type=powershell)
• "¿cuánta RAM hay?" → llama memory_info()
• "busca vulnerabilidades en este código" → llama read_file → analiza → responde
• "instala requests" → llama install_package(package="requests", manager="pip")
• "¿qué procesos usan la GPU?" → llama gpu_info()
• "escanea puertos de 192.168.1.1" → llama port_scan(host="192.168.1.1")
• "muéstrame el registro de autoruns" → llama check_persistence()
• "haz un script que X" → escribe el código + llama write_file para guardarlo

HERRAMIENTAS DISPONIBLES (úsalas directamente):
shell · read_file · edit_file (editar código) · multi_edit (varios cambios atómicos en 1 archivo) · apply_patch (diff multi-archivo) · write_file (crear) · run_python · run_tests (pytest/jest) · lint_code (ruff/bandit) · code_symbols (ubicar funciones/usos) · list_directory · search_files · grep_files
cve_lookup (NVD, gratis) · threat_intel (reputación IP/hash/URL) · yara_scan · nmap_scan · web_audit (nikto/sqlmap/ffuf) · hash_crack (john CPU / hashcat GPU) · sql_query (SQLite)
gmail_search · gmail_read · gmail_send · gdrive_search · gdrive_read · gcalendar_events (Google Workspace)
mistral_ocr · mistral_vision · mistral_transcribe · mistral_embed · mistral_code_complete (Codestral)
http_check · dns_resolve · port_check (verificar que algo funciona de verdad)
web_search · web_fetch · http_request · ssl_info · http_headers_check · dir_bruteforce
port_scan · dns_lookup · whois_lookup · traceroute · banner_grab · ping_sweep · arp_cache
strings_extract · hex_dump · file_entropy · pe_info · file_metadata
registry_query · list_services · check_persistence · network_connections
process_tree · process_info · system_info · memory_info · gpu_info · list_processes
install_package · kill_process · hash_file · diff_files · encode_decode · rag_search · rag_add
mistral_studio (búsqueda web real + intérprete de código + generación de imágenes)
mistral_consult (segunda opinión) · local_llm_consult (delegar en modelo local)
generate_document (PDF/HTML/MD) · serve_file (publicar archivo por URL)
git_op (commit/push/clone/diff/branch) · read_document (leer PDF/Excel/Word/CSV del usuario)
browse_page (navegador headless real: JS/SPA/login/formularios)
schedule_task · list_scheduled · cancel_scheduled (tareas autónomas programadas)
send_message (entregar resultados/avisos por email o Telegram)

IMPORTANTE: razona y responde SIEMPRE en español. Nunca uses inglés ni chino, ni para pensar."""

SYSTEM_PROMPT = _build_base_prompt()


def _brief_args(args: dict, max_chars: int = 240) -> str:
    try:
        text = json.dumps(args or {}, ensure_ascii=False)
    except Exception:
        text = str(args)
    return _shorten_text(text, max_chars).replace("\n", " ")


def _estimate_tokens(value) -> int:
    if value is None:
        return 0
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    return max(1, len(value) // 3)


def _tools_tokens(tools: list | None) -> int:
    schema = tools if tools is not None else TOOLS_SCHEMA
    return _estimate_tokens(schema)


def _shorten_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    keep_head = max_chars // 2
    keep_tail = max_chars - keep_head
    omitted = len(text) - max_chars
    return (
        text[:keep_head]
        + f"\n\n[... recortado: {omitted} caracteres omitidos para no superar el contexto ...]\n\n"
        + text[-keep_tail:]
    )


def _compact_message(message: dict) -> dict:
    msg = dict(message)
    content = msg.get("content") or ""
    role = msg.get("role")
    if role == "tool":
        msg["content"] = _shorten_text(content, TOOL_RESULT_CHARS)
    elif role == "assistant":
        msg["content"] = _shorten_text(content, ASSISTANT_HISTORY_CHARS)
    elif role == "user":
        msg["content"] = _shorten_text(content, USER_HISTORY_CHARS)
    return msg


def prepare_history_for_ollama(history: list, tools: list | None, budget_tokens: int = PROMPT_BUDGET_TOKENS) -> list:
    """Recorta historial antes de enviarlo a Ollama para evitar errores de contexto."""
    if not history:
        return history

    system = _compact_message(history[0]) if history[0].get("role") == "system" else None
    rest = history[1:] if system else history

    reserved = _tools_tokens(tools) + 600
    available = max(1800, budget_tokens - reserved)
    selected: list[dict] = []
    used = _estimate_tokens(system) if system else 0

    for message in reversed(rest):
        compact = _compact_message(message)
        cost = _estimate_tokens(compact)
        is_latest_user = not selected and compact.get("role") == "user"
        if used + cost <= available or is_latest_user:
            selected.append(compact)
            used += cost
        elif compact.get("role") == "user" and not any(m.get("role") == "user" for m in selected):
            compact["content"] = _shorten_text(compact.get("content") or "", 3000)
            selected.append(compact)
            used += _estimate_tokens(compact)

    selected.reverse()
    trimmed = ([system] if system else []) + selected
    if len(trimmed) == 1 and rest:
        trimmed.append(_compact_message(rest[-1]))
    return normalize_chat_history(trimmed)


def normalize_chat_history(history: list) -> list:
    normalized: list[dict] = []
    pending_tool_ids: list[str] = []
    pending_tool_calls = False

    def _has_tool_calls(message: dict) -> bool:
        return bool(message.get("tool_calls"))

    def _tool_call_ids(message: dict) -> list[str]:
        return [
            str(tool_call.get("id"))
            for tool_call in message.get("tool_calls", [])
            if isinstance(tool_call, dict) and tool_call.get("id")
        ]

    for message in history:
        role = message.get("role")
        if role not in ("system", "user", "assistant", "tool"):
            continue

        msg = dict(message)
        if role == "tool":
            if not pending_tool_calls:
                continue
            tool_call_id = msg.get("tool_call_id")
            had_pending_ids = bool(pending_tool_ids)
            if pending_tool_ids:
                if not tool_call_id or str(tool_call_id) not in pending_tool_ids:
                    continue
                pending_tool_ids.remove(str(tool_call_id))
            msg["content"] = str(msg.get("content") or "")
            normalized.append(msg)
            pending_tool_calls = bool(pending_tool_ids) if had_pending_ids else pending_tool_calls
            continue

        if (
            normalized
            and normalized[-1].get("role") == "assistant"
            and role == "assistant"
        ):
            if not _has_tool_calls(normalized[-1]) and not _has_tool_calls(msg):
                merged = dict(normalized[-1])
                merged["content"] = (merged.get("content") or "") + "\n\n" + (msg.get("content") or "")
                normalized[-1] = merged
            else:
                msg.pop("tool_calls", None)
                msg["content"] = msg.get("content") or "[respuesta anterior compactada]"
                normalized.append(msg)
            pending_tool_ids = _tool_call_ids(normalized[-1])
            pending_tool_calls = _has_tool_calls(normalized[-1])
            continue

        if role == "assistant":
            msg["content"] = msg.get("content") or ""
            pending_tool_ids = _tool_call_ids(msg)
            pending_tool_calls = _has_tool_calls(msg)
            normalized.append(msg)
            continue

        if role in ("user", "system"):
            pending_tool_ids = []
            pending_tool_calls = False
            msg["content"] = str(msg.get("content") or "")
            normalized.append(msg)
            continue

    # Ollama rejects histories that contain two assistant messages at the end of
    # the list, and some OpenAI-compatible servers reject consecutive assistant
    # messages anywhere. Compact those turns after tool validation so mobile and
    # desktop runners share the same repair path.
    compacted: list[dict] = []
    for msg in normalized:
        if (
            compacted
            and compacted[-1].get("role") == "assistant"
            and msg.get("role") == "assistant"
        ):
            prev = dict(compacted[-1])
            cur = dict(msg)
            prev_tool_calls = prev.get("tool_calls")
            cur_tool_calls = cur.get("tool_calls")
            if prev_tool_calls and not cur_tool_calls:
                text = str(cur.get("content") or "").strip()
                if text:
                    prev["content"] = (
                        str(prev.get("content") or "").rstrip()
                        + "\n\n[continuacion compactada]\n"
                        + text
                    ).strip()
                compacted[-1] = prev
                continue
            if not prev_tool_calls and cur_tool_calls:
                text = str(prev.get("content") or "").strip()
                if text:
                    cur["content"] = (text + "\n\n" + str(cur.get("content") or "")).strip()
                compacted[-1] = cur
                continue
            prev.pop("tool_calls", None)
            cur.pop("tool_calls", None)
            prev["content"] = (
                str(prev.get("content") or "").rstrip()
                + "\n\n"
                + str(cur.get("content") or "").lstrip()
            ).strip() or "[respuestas anteriores compactadas]"
            compacted[-1] = prev
            continue
        compacted.append(msg)
    normalized = compacted

    # If the final assistant still has unresolved tool calls, strip them so the
    # next request asks the model to continue instead of replaying a half turn.
    if normalized and normalized[-1].get("role") == "assistant" and normalized[-1].get("tool_calls"):
        normalized[-1] = dict(normalized[-1])
        normalized[-1].pop("tool_calls", None)
        if not normalized[-1].get("content"):
            normalized[-1]["content"] = "[tool call anterior compactado sin resultado]"
    return normalized


def is_context_overflow_error(status_code: int, body: str) -> bool:
    body_l = body.lower()
    return status_code == 400 and (
        "exceeds the available context size" in body_l
        or "exceed_context_size" in body_l
        or "n_prompt_tokens" in body_l
    )


class AgentWorker(QThread):
    token         = Signal(str)
    reasoning     = Signal(str)     # proceso/razonamiento (NO es la respuesta final)
    tool_call     = Signal(dict)    # {id, name, args, dangerous}
    tool_result   = Signal(dict)    # {id, name, result}
    need_approval = Signal(dict)    # {id, name, args, dangerous}
    finished      = Signal(str)     # full response
    error         = Signal(str)

    def __init__(self, messages, model=OLLAMA_MODEL, trusted_tools=None,
                 session_trust=False, tool_permissions=None, system_prompt=None,
                 conversation_id=None):
        super().__init__()
        self.messages         = messages
        self.model            = model
        self.trusted_tools    = trusted_tools or set()
        self.session_trust    = session_trust
        self.tool_permissions = tool_permissions or {}
        self.system_prompt    = system_prompt  # None → rebuilt per call with current date
        self.conversation_id  = conversation_id
        self._approval_event  = None
        self._approved        = None
        self._stop            = False

    def _build_system_with_rag(self) -> str:
        system = self.system_prompt if self.system_prompt is not None else _build_base_prompt()
        # A3: contexto específico de la carpeta (p.ej. "eres ingeniero…")
        folder = getattr(self, "_folder", None)
        if folder and (folder.get("context") or "").strip():
            system += (f"\n\n## CONTEXTO DE LA CARPETA «{folder['name']}»\n"
                       + folder["context"].strip()[:2000])
        last_user = ""
        for m in reversed(self.messages):
            if m["role"] == "user":
                last_user = m["content"]
                break
        if not last_user:
            return system
        try:
            from app.rag.retriever import retrieve_context
            ctx = retrieve_context(last_user, n=3)
            if ctx:
                return system + f"\n\n## CONTEXTO RELEVANTE (Knowledge Base)\n{ctx}"
        except Exception:
            pass
        return system

    def approve(self, approved: bool):
        self._approved = approved
        if self._approval_event:
            self._approval_event.set()

    def stop(self):
        self._stop = True
        ev = self._approval_event  # snapshot ref before any reassignment
        if ev:
            ev.set()  # unblock waiting approval immediately

    def run(self):
        from app.agent_log import log, log_exception, separator
        try:
            separator("AgentWorker.run()")
            # Auto-routing: elige modelo según complejidad del último mensaje
            last_user = next((m["content"] for m in reversed(self.messages)
                              if m["role"] == "user"), "")
            log("INFO", "run", "Mensaje usuario", {"msg": last_user[:200]})
            # A3: carpeta del workspace (contexto + modelo por defecto)
            self._folder = None
            try:
                from app import database as _db
                self._folder = _db.get_conversation_folder(self.conversation_id)
            except Exception:
                self._folder = None
            if (self._folder and self._folder.get("default_model")
                    and self.model in (OLLAMA_MODEL, "auto")):
                self.model = self._folder["default_model"]
                self.reasoning.emit(f"📁 Carpeta «{self._folder['name']}» → modelo {self.model}")
            try:
                from app.tools import set_exec_context
                set_exec_context(self._folder["id"] if self._folder else None, self.conversation_id)
            except Exception:
                pass
            from app.brain import is_mistral_model, is_fused, resolve_model
            if self.model in (OLLAMA_MODEL, "auto"):  # solo si no fue forzado manualmente
                try:
                    from app.model_router import route
                    routed_model, reason = route(last_user)
                    if routed_model != self.model:
                        self.model = routed_model
                        self.reasoning.emit(f"🔀 {reason}")
                except Exception:
                    pass
            self._mistral = is_mistral_model(self.model)
            self._fused = is_fused(self.model)
            if self._mistral:
                self.reasoning.emit(
                    f"🧠 Cerebro: Mistral ({resolve_model(self.model)})"
                    + (" + delegación local (fused)" if self._fused else "")
                )

            system  = self._build_system_with_rag()
            # Ancla de objetivo persistente (sobrevive a la compactación)
            if last_user:
                system += (
                    "\n\n## 🎯 OBJETIVO PERSISTENTE DE ESTA TAREA (NO LO PIERDAS)\n"
                    + last_user.strip()[:2000]
                    + "\n\nMantén SIEMPRE este objetivo en mente. Tras cada herramienta "
                    "comprueba si avanzas hacia él. No te declares terminado hasta cumplirlo "
                    "o encontrar un bloqueo concreto que expliques."
                )
            from app.memory import build_layered_history
            history = build_layered_history(system, list(self.messages), self.conversation_id)
            full    = ""

            def _parse_args(s):
                try:
                    return json.loads(s) if s.strip() else {}
                except (json.JSONDecodeError, ValueError):
                    return {}

            tools_executed  = False
            called_tool_names: set[str] = set()
            empty_tool_turns = 0
            tool_execution_count = 0

            def _emit_status(text: str):
                # Proceso/razonamiento: señal propia, separada de la respuesta final
                self.reasoning.emit(text)

            # Router: LLM elige categorías → fallback keyword → schema completo
            try:
                from app.tool_router import route_tools
                _routed_tools = route_tools(
                    last_user, list(self.messages),
                    model=self.model, ollama_url=OLLAMA_URL, use_llm=True,
                )
                log("INFO", "router", f"Tools seleccionadas: {len(_routed_tools)}",
                    [t["function"]["name"] for t in _routed_tools])
            except Exception:
                log_exception("router", "Fallo en route_tools, usando schema completo")
                from app.tools import TOOLS_SCHEMA as _routed_tools  # type: ignore

            _emit_status("Inicio la tarea y la dividiré en pasos verificables.")

            verification_done = False  # fuerza una pasada de verificación antes de cerrar
            for iteration in range(MAX_AGENT_ITERATIONS):
                if self._stop:
                    break
                if tool_execution_count >= MAX_TOOL_EXECUTIONS:
                    _emit_status("He alcanzado el presupuesto de herramientas de esta ejecución; cierro con un estado verificable.")
                    history = normalize_chat_history(history)  # fix dangling tool_calls before summary
                    history.append({
                        "role": "user",
                        "content": (
                            "No uses más herramientas. Resume el progreso, marca qué partes del objetivo están hechas, "
                            "qué falta y cuál sería el siguiente paso exacto."
                        ),
                    })
                    extra, _ = self._stream_once(history, tools=[])
                    if extra.strip():
                        full += extra
                    break

                # Expandir tools si iteración 2+ (modelo puede encadenar herramientas nuevas)
                # Contexto LEAN: routeamos una sola vez (sin re-rutear cada
                # iteración, que inflaba el esquema de tools en cada turno).

                log("INFO", "run", f"Iteración {iteration} — llamando _stream_once",
                    {"num_tools": len(_routed_tools), "history_len": len(history)})
                content, tool_calls_raw = self._stream_once(history, _routed_tools)
                log("INFO", "run", f"Iteración {iteration} — respuesta recibida",
                    {"content_len": len(content), "tool_calls": list(tool_calls_raw.keys()),
                     "content_preview": content[:200] if content else ""})
                full += content
                if tool_calls_raw and not content.strip():
                    empty_tool_turns += 1
                else:
                    empty_tool_turns = 0

                if empty_tool_turns >= EMPTY_TOOL_TURN_LIMIT:
                    _emit_status("Checkpoint: he ejecutado varias acciones sin explicación intermedia; resumo avance y continúo.")
                    history.append({
                        "role": "user",
                        "content": (
                            "Haz un checkpoint breve: qué se ha intentado, qué resultado hubo, qué falta, "
                            "y cuál es el siguiente paso. Después podrás seguir usando herramientas si hace falta."
                        ),
                    })
                    extra, _ = self._stream_once(history, tools=[])
                    if extra.strip():
                        full += extra
                        history.append({
                            "role": "user",
                            "content": "CHECKPOINT DE PROGRESO REGISTRADO:\n" + extra + "\n\nContinúa con el siguiente paso.",
                        })
                    empty_tool_turns = 0
                    continue

                if not tool_calls_raw:
                    # Verificación OBLIGATORIA: si hizo trabajo real y aún no ha
                    # verificado, le forzamos UNA pasada de comprobación con tools
                    # antes de aceptar el "hecho".
                    if tools_executed and not verification_done:
                        verification_done = True
                        log("INFO", "run", "Verificación obligatoria — forzando comprobación antes de cerrar")
                        _emit_status("Antes de cerrar, verifico que lo hecho funciona de verdad.")
                        history.append({"role": "user", "content": _VERIFY_PROMPT})
                        continue
                    log("INFO", "run", "Sin tool_calls_raw — terminando iteraciones",
                        {"tools_executed": tools_executed, "content_empty": not content.strip()})
                    # Si ejecutó tools sin generar texto → síntesis SIN tools (fuerza texto)
                    if tools_executed and not content.strip():
                        history.append({
                            "role":    "user",
                            "content": "Resume brevemente el resultado de las operaciones anteriores.",
                        })
                        extra, _ = self._stream_once(history, tools=[])
                        if extra.strip():
                            full += extra
                        else:
                            txt = "Operaciones completadas satisfactoriamente."
                            self.token.emit(txt)
                            full += txt
                    break

                # Construir lista con IDs para correlacionar resultados de tools
                tc_with_ids = {}
                for idx, v in tool_calls_raw.items():
                    tc_with_ids[idx] = {**v, "id": f"call_{iteration}_{idx}"}

                history.append({
                    "role":    "assistant",
                    "content": content or "",
                    "tool_calls": [
                        {
                            "id":       tc["id"],
                            "type":     "function",
                            "function": {"name": tc["name"],
                                         "arguments": _parse_args(tc["args_str"])},
                        }
                        for tc in tc_with_ids.values()
                    ],
                })

                for idx, tc in tc_with_ids.items():
                    if self._stop:
                        break

                    tid  = tc["id"]
                    name = tc["name"]
                    try:
                        raw_args = tc.get("args_str") or ""
                        args = json.loads(raw_args) if raw_args.strip() else {}
                    except (json.JSONDecodeError, ValueError):
                        args = {}

                    dangerous = is_dangerous(name)
                    perm      = self.tool_permissions.get(name, "ask")

                    event_payload = tool_event_payload(tid, name, args)
                    self.tool_call.emit(event_payload)
                    _emit_status(f"Voy a usar `{name}` con argumentos: {_brief_args(args)}")

                    if perm == "block":
                        result = {"blocked": True, "reason": "Herramienta bloqueada por el usuario"}
                        self.tool_result.emit({"id": tid, "name": name, "result": result})
                        history.append({"role": "tool", "tool_call_id": tid,
                                        "content": json.dumps(result)})
                        called_tool_names.add(name)
                        tools_executed = True
                        continue

                    needs_ok = (
                        name == "mistral_consult"
                        or (
                            dangerous
                            and not self.session_trust
                            and name not in self.trusted_tools
                            and perm != "auto"
                        )
                    )

                    if needs_ok:
                        import threading
                        self._approved       = None
                        self._approval_event = threading.Event()
                        if self._stop:
                            self._approval_event.set()  # already stopped — unblock immediately
                        else:
                            _emit_status(f"`{name}` necesita aprobación porque puede cambiar el sistema.")
                            self.need_approval.emit(event_payload)
                        self._approval_event.wait(timeout=60)  # 60s, no 300s
                        if not self._approved:
                            result = {"cancelled": True, "reason": "Usuario no aprobó a tiempo"}
                            history.append({"role": "tool", "tool_call_id": tid,
                                            "content": json.dumps(result)})
                            self.tool_result.emit({"id": tid, "name": name, "result": result})
                            continue

                    result = execute_tool(name, args)
                    tool_execution_count += 1
                    self.tool_result.emit({"id": tid, "name": name, "result": result})
                    _emit_status(f"`{name}` terminó; incorporo el resultado y decido el siguiente paso.")
                    history.append({"role": "tool", "tool_call_id": tid,
                                    "content": json.dumps(result, ensure_ascii=False)})
                    called_tool_names.add(name)
                    tools_executed = True

            # Safety net: loop agotó iteraciones sin generar texto
            if not full.strip() and tools_executed and not self._stop:
                history = normalize_chat_history(history)  # fix dangling tool_calls before summary
                history.append({
                    "role":    "user",
                    "content": "Resume brevemente el resultado de las operaciones anteriores.",
                })
                try:
                    extra, _ = self._stream_once(history, tools=[])
                    if extra.strip():
                        full += extra
                except Exception:
                    pass

            # Fallback final: si el modelo nunca generó texto (ni con síntesis)
            if not full.strip():
                fallback = ("⚠️ El agente ejecutó las herramientas pero no generó respuesta. "
                            "Consulta los resultados en el panel lateral.")
                self.token.emit(fallback)
                full = fallback

            self.finished.emit(full)

        except Exception as e:
            import traceback as _tb
            log_exception("run", f"Excepción en AgentWorker: {type(e).__name__}: {e}")
            self.error.emit(f"{type(e).__name__}: {e}\n\n{_tb.format_exc()}")

    @staticmethod
    def _auto_ctx(history: list) -> int:
        total_chars = 0
        for m in history:
            total_chars += len(m.get("content") or "")
            for tc in m.get("tool_calls", []):
                total_chars += len(json.dumps(tc, ensure_ascii=False))
        tokens_now    = total_chars // 3
        # Add ~5500 tokens reserved for the tools schema (38 tools × ~145 tokens each)
        tokens_needed = int(tokens_now * 2.5) + 5500
        if tokens_needed < 6000:  return 10240
        return MAX_CTX

    def _stream_once(self, history: list, tools: list | None = None) -> tuple[str, dict]:
        from app.agent_log import log, log_exception
        import time

        _tools_used = tools if tools is not None else TOOLS_SCHEMA

        # ── Backend Mistral (nube) ───────────────────────────────────────────
        if getattr(self, "_mistral", False):
            from app.brain import stream_mistral
            try:
                content, tool_calls, _r = stream_mistral(
                    self.model, history, _tools_used,
                    emit_token=lambda d: self.token.emit(d),
                    emit_reasoning=lambda d: self.reasoning.emit(d),
                    should_stop=lambda: self._stop,
                )
                # Adaptar forma {idx:{name,args}} → {idx:{name,args_str}} del desktop
                adapted = {i: {"name": v["name"], "args_str": v["args"]}
                           for i, v in tool_calls.items()}
                return content, adapted
            except Exception as exc:
                log_exception("stream_once", f"Mistral falló: {exc} — fallback local")
                self.reasoning.emit(f"⚠️ Mistral falló ({exc}); sigo con el modelo local.")
                self._mistral = False
                from app.model_router import FAST_MODEL
                self.model = FAST_MODEL

        # ── Backend Ollama (local) ───────────────────────────────────────────
        history = prepare_history_for_ollama(history, _tools_used)
        num_ctx = self._auto_ctx(history)
        log("INFO", "stream_once", "Iniciando llamada Ollama",
            {"model": self.model, "num_ctx": num_ctx,
             "num_tools": len(_tools_used), "history_msgs": len(history)})
        payload = {
            "model":    self.model,
            "messages": history,
            "tools":    _tools_used,
            "stream":   True,
            # Thinking nativo OFF por defecto (inestable en streaming+tools con este
            # abliterado). Interruptor: CYBERAGENT_THINK=1.
            "think":    os.environ.get("CYBERAGENT_THINK", "0") == "1"
                        and any(t in (self.model or "").lower() for t in ("qwen3", "huihui")),
            "options":  {"num_ctx": num_ctx, "temperature": 0.3, "top_p": 0.95,
                         "repeat_penalty": 1.05, "top_k": 40},
        }

        # 300s read: cubre carga del modelo desde disco (14GB GGUF → 2-4 min en NVMe)
        _t = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=5.0)

        MAX_ATTEMPTS = 3
        RETRY_WAIT   = 25  # segundos entre reintentos

        from app.brain import split_think, strip_lead_artifacts
        for attempt in range(MAX_ATTEMPTS):
            content        = ""
            tool_calls_raw = {}
            _think_state   = False   # parser de <think> para el stream local
            try:
                with httpx.Client(timeout=_t) as client:
                    with client.stream("POST", OLLAMA_URL, json=payload) as resp:
                        if resp.status_code != 200:
                            body = resp.read().decode("utf-8", errors="replace")
                            if is_context_overflow_error(resp.status_code, body):
                                raise RuntimeError(
                                    "Ollama rechazo la peticion porque el prompt supera el contexto "
                                    f"disponible ({MAX_CTX} tokens). El historial ya se recorto; "
                                    "reduce el mensaje actual o usa menos herramientas para esta llamada. "
                                    f"Detalle: {body[:500]}"
                                )
                            raise RuntimeError(f"Ollama error {resp.status_code}: {body[:500]}")

                        for line in resp.iter_lines():
                            if self._stop:
                                break
                            if not line.strip():
                                continue
                            try:
                                chunk = json.loads(line)
                            except (json.JSONDecodeError, ValueError):
                                continue

                            if "error" in chunk:
                                raise RuntimeError(f"Ollama: {chunk['error']}")

                            msg   = chunk.get("message", {})
                            tdelta = msg.get("thinking", "")
                            if tdelta:   # razonamiento nativo (campo separado)
                                self.reasoning.emit(tdelta)
                            delta = msg.get("content", "")
                            if delta:
                                # Separa <think> inline (modo herramientas) → proceso
                                _r, _c, _think_state = split_think(delta, _think_state)
                                if _r:
                                    self.reasoning.emit(_r)
                                if _c:
                                    if not content:
                                        _c = strip_lead_artifacts(_c)
                                    if _c:
                                        content += _c
                                        self.token.emit(_c)

                            for tc in msg.get("tool_calls", []):
                                idx = tc.get("index", len(tool_calls_raw))
                                fn  = tc.get("function", {})
                                if idx not in tool_calls_raw:
                                    tool_calls_raw[idx] = {"name": "", "args_str": ""}
                                if fn.get("name"):
                                    tool_calls_raw[idx]["name"] = fn["name"]
                                args = fn.get("arguments", "")
                                if isinstance(args, dict):
                                    args = json.dumps(args, ensure_ascii=False)
                                tool_calls_raw[idx]["args_str"] += args

                            if chunk.get("done"):
                                log("INFO", "stream_once", "done=True recibido",
                                    {"content_len": len(content),
                                     "tool_calls_count": len(tool_calls_raw)})
                                try:
                                    from app import local_usage
                                    local_usage.log_local(
                                        chunk.get("prompt_eval_count", 0),
                                        chunk.get("eval_count", 0),
                                        model=self.model, context="agent")
                                except Exception:
                                    pass
                                break

                # Éxito — salir del loop de reintentos
                log("INFO", "stream_once", "Llamada completada OK",
                    {"content_len": len(content), "tool_calls": list(tool_calls_raw.keys())})
                break

            except httpx.ReadTimeout:
                log("WARN", "stream_once", f"ReadTimeout intento {attempt}",
                    {"content_partial": content[:100] if content else ""})
                # Dos causas: (1) modelo cargándose a VRAM, (2) contexto muy largo
                if content:
                    # Tenemos respuesta parcial — devolverla en vez de reintentar
                    return content, tool_calls_raw
                if attempt < MAX_ATTEMPTS - 1:
                    wait = RETRY_WAIT * (attempt + 1)
                    self.token.emit(
                        f"\n[⏳ Ollama cargando modelo a VRAM... "
                        f"reintentando en {wait}s ({attempt + 1}/{MAX_ATTEMPTS - 1})]\n\n"
                    )
                    time.sleep(wait)
                    continue
                raise RuntimeError(
                    f"Ollama no respondió tras {MAX_ATTEMPTS} intentos.\n"
                    "El modelo puede estar cargándose o sin VRAM suficiente. "
                    "Espera unos minutos y reintenta."
                )

            except (httpx.ConnectError, httpx.ConnectTimeout):
                log("ERROR", "stream_once", f"ConnectError intento {attempt}")
                # Ollama no está corriendo — intentar arrancarlo automáticamente
                if attempt < MAX_ATTEMPTS - 1:
                    self.token.emit(
                        f"\n[🔄 Ollama no responde — arrancando automáticamente... "
                        f"({attempt + 1}/{MAX_ATTEMPTS - 1})]\n\n"
                    )
                    if _autostart_ollama():
                        time.sleep(3)   # pequeña pausa extra para que el modelo se registre
                        continue
                raise RuntimeError(
                    "No se puede arrancar Ollama automáticamente.\n"
                    "Abre una terminal y ejecuta: ollama serve\n"
                    "Luego reintenta tu mensaje."
                )

            except httpx.ReadError:
                if content:
                    return content, tool_calls_raw
                raise RuntimeError(
                    "Ollama cerró la conexión inesperadamente.\n"
                    "Posibles causas: sin VRAM, modelo descargado, o contexto demasiado largo."
                )

        return content, tool_calls_raw
