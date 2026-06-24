import json, socket, subprocess, time, httpx
from PySide6.QtCore import QThread, Signal
from app.tools import TOOLS_SCHEMA, execute_tool, is_dangerous

OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "cyberagent-original"
MAX_CTX = 12288
PROMPT_BUDGET_TOKENS = 10500
TOOL_RESULT_CHARS = 4000
ASSISTANT_HISTORY_CHARS = 6000
USER_HISTORY_CHARS = 8000
EMPTY_TOOL_TURN_LIMIT = 3
MAX_AGENT_ITERATIONS = 30
MAX_TOOL_EXECUTIONS = 40


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

def _build_base_prompt() -> str:
    from datetime import datetime
    return f"""Eres CyberAgent, agente autónomo de steve. {datetime.now().strftime("%d/%m/%Y %H:%M")}
Sistema: RTX 5080 16GB · 64GB DDR5 · Win11 Pro + WSL2 · Python 3.14
Proyecto: C:\\Users\\steve\\cyber-llm\\agent-native

REGLA DE TRABAJO: Antes de actuar, di en 1 frase qué vas a comprobar o ejecutar.
Si necesitas herramientas, úsalas y mantén al usuario informado con pasos breves.
Cuando termines, entrega una conclusión clara: hecho, bloqueado o siguiente acción.
Para tareas largas, trabaja por fases: plan corto, ejecución, verificación y siguiente paso.
Mantén un checklist mental del objetivo y continúa hasta completarlo o encontrar un bloqueo concreto.
No encadenes herramientas indefinidamente sin explicar progreso: cada pocas acciones emite un checkpoint.
Si una fase falla, intenta una alternativa razonable antes de declarar bloqueo.

EJEMPLOS DE COMPORTAMIENTO CORRECTO:
• "haz que main.py imprima hola" → llama read_file(path=main.py) → llama write_file con cambio → listo
• "ejecuta el servidor" → llama shell(command="python main.py", shell_type=powershell)
• "¿cuánta RAM hay?" → llama memory_info()
• "busca vulnerabilidades en este código" → llama read_file → analiza → responde
• "instala requests" → llama install_package(package="requests", manager="pip")
• "¿qué procesos usan la GPU?" → llama gpu_info()
• "escanea puertos de 192.168.1.1" → llama port_scan(host="192.168.1.1")
• "muéstrame el registro de autoruns" → llama check_persistence()
• "haz un script que X" → escribe el código + llama write_file para guardarlo

HERRAMIENTAS DISPONIBLES (úsalas directamente):
shell · read_file · write_file · run_python · list_directory · search_files · grep_files
web_search · web_fetch · http_request · ssl_info · http_headers_check · dir_bruteforce
port_scan · dns_lookup · whois_lookup · traceroute · banner_grab · ping_sweep · arp_cache
strings_extract · hex_dump · file_entropy · pe_info · file_metadata
registry_query · list_services · check_persistence · network_connections
process_tree · process_info · system_info · memory_info · gpu_info · list_processes
install_package · kill_process · hash_file · diff_files · encode_decode · rag_search · rag_add

Responde en español."""

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
        self.system_prompt    = system_prompt or SYSTEM_PROMPT
        self.conversation_id  = conversation_id
        self._approval_event  = None
        self._approved        = None
        self._stop            = False

    def _build_system_with_rag(self) -> str:
        system = self.system_prompt or _build_base_prompt()
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
            if self.model == OLLAMA_MODEL:  # solo si no fue forzado manualmente
                try:
                    from app.model_router import route
                    routed_model, reason = route(last_user)
                    if routed_model != self.model:
                        self.model = routed_model
                        self.token.emit(f"[🔀 {reason}]\n\n")
                except Exception:
                    pass

            system  = self._build_system_with_rag()
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
                msg = f"\n\n[estado] {text}\n\n"
                self.token.emit(msg)

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

            for iteration in range(MAX_AGENT_ITERATIONS):
                if self._stop:
                    break
                if tool_execution_count >= MAX_TOOL_EXECUTIONS:
                    _emit_status("He alcanzado el presupuesto de herramientas de esta ejecución; cierro con un estado verificable.")
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
                if iteration > 0 and called_tool_names:
                    try:
                        from app.tool_router import route_tools
                        _routed_tools = route_tools(
                            last_user, history, called_tool_names
                        )
                    except Exception:
                        pass

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

                    self.tool_call.emit({"id": tid, "name": name, "args": args, "dangerous": dangerous})
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
                        dangerous
                        and not self.session_trust
                        and name not in self.trusted_tools
                        and perm != "auto"
                    )

                    if needs_ok:
                        import threading
                        self._approved       = None
                        self._approval_event = threading.Event()
                        if not self._stop:  # guard: stop() may have fired before we created event
                            _emit_status(f"`{name}` necesita aprobación porque puede cambiar el sistema.")
                            self.need_approval.emit({"id": tid, "name": name, "args": args, "dangerous": dangerous})
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

            # Safety net: loop agotó 15 iteraciones sin generar texto
            if not full.strip() and tools_executed and not self._stop:
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
            "options":  {"num_ctx": num_ctx, "temperature": 0.6, "top_p": 0.9,
                         "repeat_penalty": 1.05, "top_k": 40},
        }

        # 300s read: cubre carga del modelo desde disco (14GB GGUF → 2-4 min en NVMe)
        _t = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=5.0)

        MAX_ATTEMPTS = 3
        RETRY_WAIT   = 25  # segundos entre reintentos

        for attempt in range(MAX_ATTEMPTS):
            content        = ""
            tool_calls_raw = {}
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
                            delta = msg.get("content", "")
                            if delta:
                                content += delta
                                self.token.emit(delta)

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
