"""Agente no-Qt para uso en el servidor FastAPI local."""
import json, threading, queue, sys, os

def _parse_args(s: str) -> dict:
    try:
        return json.loads(s) if s.strip() else {}
    except Exception:
        return {}
import httpx

_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.tools import TOOLS_SCHEMA, execute_tool, is_dangerous
from app.ollama_client import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    SYSTEM_PROMPT,
    EMPTY_TOOL_TURN_LIMIT,
    MAX_AGENT_ITERATIONS,
    MAX_TOOL_EXECUTIONS,
    MAX_CTX,
    _brief_args,
    is_context_overflow_error,
    prepare_history_for_ollama,
)


class AgentRunner:
    """Ejecuta el agente en un hilo y emite eventos SSE-style."""

    def __init__(
        self,
        messages: list,
        model: str              = OLLAMA_MODEL,
        session_trust: bool     = False,
        tool_permissions: dict  = None,
        device_context: str     = "PC (escritorio)",
        conversation_id         = None,
    ):
        self.messages         = messages
        self.model            = model
        self.session_trust    = session_trust
        self.tool_permissions = tool_permissions or {}
        self.device_context   = device_context
        self.conversation_id  = conversation_id
        self._q               = queue.Queue()
        self._approvals: dict[str, threading.Event] = {}
        self._approval_res: dict[str, bool]         = {}
        self._stop_flag                             = False

    def approve(self, tool_id: str, approved: bool):
        self._approval_res[tool_id] = approved
        ev = self._approvals.get(tool_id)
        if ev:
            ev.set()

    def stop(self):
        self._stop_flag = True
        for ev in self._approvals.values():
            ev.set()  # unblock any pending approval waits immediately

    def events(self):
        """Generador — devuelve dicts hasta {type: done} o {type: error}."""
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        while True:
            try:
                evt = self._q.get(timeout=1.0)
                yield evt
                if evt["type"] in ("done", "error"):
                    break
            except queue.Empty:
                if not t.is_alive():
                    yield {"type": "done", "data": ""}
                    break

    def _run(self):
        try:
            # Auto-routing
            last_user = next((m["content"] for m in reversed(self.messages)
                              if m["role"] == "user"), "")
            if self.model == OLLAMA_MODEL:
                try:
                    from app.model_router import route
                    routed_model, reason = route(last_user)
                    if routed_model != self.model:
                        self.model = routed_model
                        self._q.put({"type": "token", "data": f"[🔀 {reason}]\n\n"})
                except Exception:
                    pass

            from app.ollama_client import _build_base_prompt
            system = _build_base_prompt() + (
                f"\n\nSESIÓN: El usuario habla desde {self.device_context}.\n"
                f"- Móvil Android: usa herramientas mobile_* (ADB).\n"
                f"- iPhone: usa ios_shell (SSH).\n"
                f"- PC: acceso total al sistema Windows."
            )

            last_user = next(
                (m["content"] for m in reversed(self.messages) if m["role"] == "user"), ""
            )
            if last_user:
                try:
                    from app.rag.retriever import retrieve_context
                    ctx = retrieve_context(last_user)
                    if ctx:
                        system += f"\n\n## CONTEXTO RELEVANTE\n{ctx}"
                except Exception:
                    pass

            from app.memory import build_layered_history
            history = build_layered_history(system, list(self.messages), self.conversation_id)
            full    = ""
            tools_executed    = False
            called_tool_names: set = set()
            empty_tool_turns = 0
            tool_execution_count = 0

            def _emit_status(text: str):
                msg = f"\n\n[estado] {text}\n\n"
                self._q.put({"type": "token", "data": msg})

            try:
                from app.tool_router import route_tools
                from app.ollama_client import OLLAMA_URL
                _routed_tools = route_tools(
                    last_user, list(self.messages),
                    model=self.model, ollama_url=OLLAMA_URL, use_llm=True,
                )
            except Exception:
                from app.tools import TOOLS_SCHEMA as _routed_tools  # type: ignore

            _emit_status("Inicio la tarea y la dividiré en pasos verificables.")

            for iteration in range(MAX_AGENT_ITERATIONS):
                if self._stop_flag:
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
                        self._q.put({"type": "token", "data": extra})
                        full += extra
                    break
                if iteration > 0 and called_tool_names:
                    try:
                        from app.tool_router import route_tools
                        _routed_tools = route_tools(last_user, history, called_tool_names)
                    except Exception:
                        pass
                content, tool_calls = self._stream_once(history, _routed_tools)
                full += content
                if tool_calls and not content.strip():
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
                        self._q.put({"type": "token", "data": extra})
                        full += extra
                        history.append({
                            "role": "user",
                            "content": "CHECKPOINT DE PROGRESO REGISTRADO:\n" + extra + "\n\nContinúa con el siguiente paso.",
                        })
                    empty_tool_turns = 0
                    continue
                if not tool_calls:
                    if tools_executed and not content.strip():
                        history.append({
                            "role":    "user",
                            "content": "Resume brevemente el resultado de las operaciones anteriores.",
                        })
                        extra, _ = self._stream_once(history, tools=[])
                        if extra.strip():
                            full += extra
                            self._q.put({"type": "token", "data": extra})
                        else:
                            txt = "Operaciones completadas satisfactoriamente."
                            self._q.put({"type": "token", "data": txt})
                            full += txt
                    break

                # IDs para correlacionar resultados
                tc_with_ids = {}
                for idx, v in tool_calls.items():
                    tc_with_ids[idx] = {**v, "id": f"api_{iteration}_{idx}"}

                history.append({
                    "role":       "assistant",
                    "content":    content or "",
                    "tool_calls": [
                        {
                            "id":       tc["id"],
                            "type":     "function",
                            "function": {
                                "name":      tc["name"],
                                "arguments": _parse_args(tc["args"]),
                            },
                        }
                        for tc in tc_with_ids.values()
                    ],
                })

                for idx, tc in tc_with_ids.items():
                    if self._stop_flag:
                        break
                    tid  = tc["id"]
                    name = tc["name"]
                    try:
                        raw_args = tc.get("args") or ""
                        args = json.loads(raw_args) if raw_args.strip() else {}
                    except Exception:
                        args = {}

                    dangerous = is_dangerous(name)
                    perm      = self.tool_permissions.get(name, "ask")

                    self._q.put({"type": "tool_call",
                                 "data": {"id": tid, "name": name,
                                          "args": args, "dangerous": dangerous}})
                    _emit_status(f"Voy a usar `{name}` con argumentos: {_brief_args(args)}")

                    if perm == "block":
                        result = {"blocked": True}
                    elif dangerous and not self.session_trust and perm != "auto":
                        ev = threading.Event()
                        self._approvals[tid] = ev
                        _emit_status(f"`{name}` necesita aprobación porque puede cambiar el sistema.")
                        self._q.put({"type": "need_approval",
                                     "data": {"id": tid, "name": name, "args": args}})
                        ev.wait(timeout=60)
                        if self._approval_res.get(tid, False):
                            result = execute_tool(name, args)
                        else:
                            result = {"cancelled": True, "reason": "user_timeout", "tool": name}
                    else:
                        result = execute_tool(name, args)

                    if not result.get("blocked") and not result.get("cancelled"):
                        tool_execution_count += 1

                    history.append({"role": "tool", "tool_call_id": tid,
                                    "content": json.dumps(result, ensure_ascii=False)})
                    self._q.put({"type": "tool_result",
                                 "data": {"id": tid, "result": result}})

                    if result.get("cancelled"):
                        history.append({
                            "role": "user",
                            "content": (
                                f"La herramienta `{name}` fue cancelada (timeout de aprobación). "
                                "No reintentes herramientas peligrosas. "
                                "Resume lo que se completó hasta ahora."
                            ),
                        })
                        break

                    _emit_status(f"`{name}` terminó; incorporo el resultado y decido el siguiente paso.")
                    called_tool_names.add(name)
                    tools_executed = True

            if not full.strip() and tools_executed and not self._stop_flag:
                history.append({
                    "role": "user",
                    "content": "Resume brevemente el resultado de las operaciones anteriores.",
                })
                try:
                    extra, _ = self._stream_once(history, tools=[])
                    if extra.strip():
                        self._q.put({"type": "token", "data": extra})
                        full += extra
                except Exception:
                    pass

            if not full.strip():
                fallback = ("⚠️ El agente ejecutó las herramientas pero no generó respuesta. "
                            "Consulta los resultados en el panel lateral.")
                self._q.put({"type": "token", "data": fallback})
                full = fallback

            self._q.put({"type": "done", "data": full})
        except Exception as exc:
            import traceback
            self._q.put({"type": "error", "data": str(exc) + "\n" + traceback.format_exc()})

    @staticmethod
    def _auto_ctx(history: list) -> int:
        total_chars = 0
        for m in history:
            total_chars += len(m.get("content") or "")
            for tc in m.get("tool_calls", []):
                total_chars += len(json.dumps(tc, ensure_ascii=False))
        tokens_now    = total_chars // 3
        tokens_needed = int(tokens_now * 2.5) + 5500  # +5500 for tools schema overhead
        if tokens_needed < 6000:  return 10240
        return MAX_CTX

    def _stream_once(self, history: list, tools: list | None = None) -> tuple[str, dict]:
        import time

        _tools_used = tools if tools is not None else TOOLS_SCHEMA
        history = prepare_history_for_ollama(history, _tools_used)
        num_ctx = self._auto_ctx(history)
        payload = {
            "model":    self.model,
            "messages": history,
            "tools":    _tools_used,
            "stream":   True,
            "options":  {"num_ctx": num_ctx, "temperature": 0.6, "top_p": 0.9,
                         "repeat_penalty": 1.05, "top_k": 40},
        }
        _t = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=5.0)
        MAX_ATTEMPTS = 3
        RETRY_WAIT   = 25

        for attempt in range(MAX_ATTEMPTS):
            content    = ""
            tool_calls: dict = {}
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
                            if self._stop_flag:
                                break
                            if not line.strip():
                                continue
                            try:
                                chunk = json.loads(line)
                            except Exception:
                                continue
                            if "error" in chunk:
                                raise RuntimeError(f"Ollama: {chunk['error']}")
                            msg   = chunk.get("message", {})
                            delta = msg.get("content", "")
                            if delta:
                                content += delta
                                self._q.put({"type": "token", "data": delta})
                            for tc in msg.get("tool_calls", []):
                                idx = tc.get("index", len(tool_calls))
                                fn  = tc.get("function", {})
                                if idx not in tool_calls:
                                    tool_calls[idx] = {"name": "", "args": ""}
                                if fn.get("name"):
                                    tool_calls[idx]["name"] = fn["name"]
                                args = fn.get("arguments", "")
                                if isinstance(args, dict):
                                    args = json.dumps(args, ensure_ascii=False)
                                tool_calls[idx]["args"] += args
                            if chunk.get("done"):
                                break
                break  # éxito

            except httpx.ReadTimeout:
                if content:
                    return content, tool_calls
                if attempt < MAX_ATTEMPTS - 1:
                    wait = RETRY_WAIT * (attempt + 1)
                    self._q.put({"type": "token",
                                 "data": f"\n[⏳ Ollama cargando modelo... reintentando en {wait}s "
                                         f"({attempt + 1}/{MAX_ATTEMPTS - 1})]\n\n"})
                    time.sleep(wait)
                    continue
                raise RuntimeError(
                    f"Ollama no respondió tras {MAX_ATTEMPTS} intentos.\n"
                    "El modelo puede estar cargándose o sin VRAM suficiente."
                )

            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt < MAX_ATTEMPTS - 1:
                    self._q.put({"type": "token",
                                 "data": f"\n[🔄 Ollama no responde — arrancando... "
                                         f"({attempt + 1}/{MAX_ATTEMPTS - 1})]\n\n"})
                    from app.ollama_client import _autostart_ollama
                    if _autostart_ollama():
                        time.sleep(3)
                        continue
                raise RuntimeError(
                    "No se puede arrancar Ollama automáticamente.\n"
                    "Ejecuta 'ollama serve' en una terminal y reintenta."
                )

            except httpx.ReadError:
                if content:
                    return content, tool_calls
                raise RuntimeError(
                    "Ollama cerró la conexión inesperadamente.\n"
                    "Posibles causas: sin VRAM, modelo descargado, o contexto demasiado largo."
                )

        return content, tool_calls
