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

from app.tools import TOOLS_SCHEMA, execute_tool, is_dangerous, tool_event_payload
from app.ollama_client import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    SYSTEM_PROMPT,
    EMPTY_TOOL_TURN_LIMIT,
    MAX_AGENT_ITERATIONS,
    MAX_TOOL_EXECUTIONS,
    MAX_CTX,
    FAST_KEEP_ALIVE,
    POWER_KEEP_ALIVE,
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
        expert_mode: bool       = False,
        folder_id               = None,
    ):
        self.messages         = messages
        self.model            = model
        self.session_trust    = session_trust
        self.tool_permissions = tool_permissions or {}
        self.device_context   = device_context
        self.conversation_id  = conversation_id
        self.expert_mode      = expert_mode
        self.folder_id        = folder_id
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

    def _build_cost(self) -> dict:
        """Coste de ESTA respuesta (diff de sesión) + acumulado del mes (todos los
        modelos): Mistral (gasto real) + local (ahorro, gasto $0)."""
        from app import mistral_usage as _mu, local_usage as _lu
        st = self._cost_start or {}
        ms = _mu.session_summary(); ls = _lu.session_summary()
        m_in = ms.get("input", 0) - st.get("m_in", 0)
        m_out = ms.get("output", 0) - st.get("m_out", 0)
        m_cost = ms.get("cost", 0.0) - st.get("m_cost", 0.0)
        l_in = ls.get("input", 0) - st.get("l_in", 0)
        l_out = ls.get("output", 0) - st.get("l_out", 0)
        l_saved = ls.get("saved", 0.0) - st.get("l_saved", 0.0)
        used_cloud = (m_in + m_out) > 0
        this = {
            "model": self.model,
            "is_local": not used_cloud,
            "input_tokens": (m_in if used_cloud else l_in),
            "output_tokens": (m_out if used_cloud else l_out),
            "cost_usd": round(m_cost, 6),          # gasto real (0 si local)
            "saved_usd": round(l_saved, 6),        # ahorrado si fue local
        }
        this["tokens"] = this["input_tokens"] + this["output_tokens"]
        mu_month = _mu.get_summary("month"); lu_month = _lu.get_summary("month")
        month = {
            "cost_usd": round(mu_month["cost_usd"], 4),               # gasto real del mes
            "cloud_tokens": mu_month["input_tokens"] + mu_month["output_tokens"],
            "cloud_calls": mu_month["calls"],
            "local_tokens": lu_month["input_tokens"] + lu_month["output_tokens"],
            "local_saved_usd": round(lu_month["saved_usd"], 4),
            "local_calls": lu_month["calls"],
        }
        return {"this": this, "month": month}

    def _run(self):
        # WEBPROD-009: snapshot de uso al empezar, para calcular el coste de ESTA
        # respuesta (diff contra los totales de sesión al terminar).
        try:
            from app import mistral_usage as _mu, local_usage as _lu
            self._cost_start = {
                "m_in": _mu.session_summary().get("input", 0),
                "m_out": _mu.session_summary().get("output", 0),
                "m_cost": _mu.session_summary().get("cost", 0.0),
                "l_in": _lu.session_summary().get("input", 0),
                "l_out": _lu.session_summary().get("output", 0),
                "l_saved": _lu.session_summary().get("saved", 0.0),
            }
        except Exception:
            self._cost_start = None
        try:
            # Auto-routing
            last_user = next((m["content"] for m in reversed(self.messages)
                              if m["role"] == "user"), "")
            # A3: carpeta del workspace (contexto + modelo por defecto)
            self._folder = None
            try:
                from app import database as _db
                self._folder = (_db.get_folder(self.folder_id) if self.folder_id
                                else _db.get_conversation_folder(self.conversation_id))
            except Exception:
                self._folder = None
            # El modelo por defecto de la carpeta MANDA si el usuario está en auto/local
            if (self._folder and self._folder.get("default_model")
                    and self.model in (OLLAMA_MODEL, "auto")):
                self.model = self._folder["default_model"]
                self._q.put({"type": "reasoning",
                             "data": f"📁 Carpeta «{self._folder['name']}» → modelo {self.model}"})
            try:
                from app.tools import set_exec_context
                set_exec_context(self._folder["id"] if self._folder else self.folder_id,
                                 self.conversation_id)
            except Exception:
                pass
            from app.brain import is_mistral_model, is_fused, resolve_model
            if self.model in (OLLAMA_MODEL, "auto"):
                try:
                    from app.model_router import route
                    routed_model, reason = route(last_user)
                    if routed_model != self.model:
                        self.model = routed_model
                        self._q.put({"type": "reasoning", "data": f"🔀 {reason}"})
                except Exception:
                    pass
            self._mistral = is_mistral_model(self.model)
            self._fused = is_fused(self.model)
            if self._mistral:
                self._q.put({"type": "reasoning",
                             "data": f"🧠 Cerebro: Mistral ({resolve_model(self.model)})"
                                     + (" + delegación local (fused)" if self._fused else "")})

            from app.ollama_client import _build_base_prompt
            system = _build_base_prompt() + (
                f"\n\nSESIÓN: El usuario habla desde {self.device_context}.\n"
                f"- Móvil Android: usa herramientas mobile_* (ADB).\n"
                f"- iPhone: usa ios_shell (SSH).\n"
                f"- PC: acceso total al sistema Windows."
            )

            # A3/WEBPROD-010: contexto de la carpeta + herencia desde la categoría
            # padre (categoría → subcategoría/proyecto). Raíz primero.
            if self._folder:
                try:
                    from app import database as _db
                    chain = _db.folder_context_chain(self._folder["id"])
                except Exception:
                    chain = [self._folder]
                for fld in chain:
                    ctx = (fld.get("context") or "").strip()
                    if ctx:
                        system += (f"\n\n## CONTEXTO DE «{fld['name']}»\n" + ctx[:2000])

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

            # Ancla de objetivo: se fija en el system prompt y NUNCA se compacta,
            # para que el modelo no pierda el objetivo en tareas largas.
            if last_user:
                system += (
                    "\n\n## 🎯 OBJETIVO PERSISTENTE DE ESTA TAREA (NO LO PIERDAS)\n"
                    + last_user.strip()[:2000]
                    + "\n\nMantén SIEMPRE este objetivo en mente. Tras cada herramienta, "
                    "comprueba si avanzas hacia él. No te declares terminado hasta cumplirlo "
                    "o encontrar un bloqueo concreto que expliques."
                )

            from app.memory import build_layered_history
            history = build_layered_history(system, list(self.messages), self.conversation_id)
            full    = ""
            tools_executed    = False
            called_tool_names: set = set()
            empty_tool_turns = 0
            tool_execution_count = 0

            def _emit_status(text: str):
                # Razonamiento/proceso: evento propio (NO se mezcla con la respuesta final)
                self._q.put({"type": "reasoning", "data": text})

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

            verification_done = False  # fuerza una pasada de verificación antes de cerrar
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
                # Contexto LEAN: routeamos UNA sola vez al inicio y reutilizamos el
                # set toda la ejecución. Antes re-routeábamos cada iteración, lo que
                # inflaba el esquema de tools que ve el modelo en cada turno (más
                # tokens, más coste, más distracción). _ALWAYS cubre lo esencial.
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
                    # Verificación OBLIGATORIA: una pasada de comprobación con tools
                    # antes de aceptar que la tarea está hecha.
                    if tools_executed and not verification_done:
                        verification_done = True
                        from app.ollama_client import _VERIFY_PROMPT
                        _emit_status("Antes de cerrar, verifico que lo hecho funciona de verdad.")
                        history.append({"role": "user", "content": _VERIFY_PROMPT})
                        continue
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

                # PARALELO (seguro): si el turno trae ≥2 herramientas y TODAS son
                # de solo-lectura/seguras (no peligrosas, sin aprobación), se ejecutan
                # a la vez. En cuanto hay una peligrosa, cae al camino secuencial de
                # abajo con su aprobación intacta. Acelera p.ej. escanear varios hosts.
                _parallel_ok = len(tc_with_ids) >= 2 and all(
                    (not is_dangerous(tc["name"])) and tc["name"] != "mistral_consult"
                    and self.tool_permissions.get(tc["name"], "ask") != "block"
                    for tc in tc_with_ids.values()
                )
                if _parallel_ok and not self._stop_flag:
                    import concurrent.futures
                    _parsed = {}
                    for tc in tc_with_ids.values():
                        try:
                            _ra = tc.get("args") or ""
                            _a = json.loads(_ra) if _ra.strip() else {}
                        except Exception:
                            _a = {}
                        _parsed[tc["id"]] = (tc["name"], _a)
                        self._q.put({"type": "tool_call",
                                     "data": tool_event_payload(tc["id"], tc["name"], _a)})
                    _emit_status(f"Ejecuto {len(_parsed)} herramientas en paralelo.")
                    _results = {}
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(_parsed))) as _ex:
                        _futs = {_ex.submit(execute_tool, n, a): t for t, (n, a) in _parsed.items()}
                        for _f in concurrent.futures.as_completed(_futs):
                            _t = _futs[_f]
                            try:
                                _results[_t] = _f.result()
                            except Exception as _e:
                                _results[_t] = {"ok": False, "error": str(_e)}
                    for tc in tc_with_ids.values():  # historial en orden original
                        _tid = tc["id"]
                        _name = _parsed[_tid][0]
                        _res = _results.get(_tid, {})
                        if not _res.get("blocked") and not _res.get("cancelled"):
                            tool_execution_count += 1
                        history.append({"role": "tool", "tool_call_id": _tid,
                                        "content": json.dumps(_res, ensure_ascii=False)})
                        self._q.put({"type": "tool_result", "data": {"id": _tid, "result": _res}})
                        if _res.get("watch_started"):
                            self._q.put({"type": "watch_config", "data": _res})
                        if _res.get("watch_stopped"):
                            self._q.put({"type": "watch_stop", "data": {}})
                        called_tool_names.add(_name)
                        tools_executed = True
                    _emit_status("Herramientas en paralelo completadas; decido el siguiente paso.")
                    continue

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

                    event_payload = tool_event_payload(tid, name, args)
                    self._q.put({"type": "tool_call", "data": event_payload})
                    _emit_status(f"Voy a usar `{name}` con argumentos: {_brief_args(args)}")

                    if perm == "block":
                        result = {"blocked": True}
                    elif name == "mistral_consult" or (dangerous and not self.session_trust and perm != "auto"):
                        ev = threading.Event()
                        self._approvals[tid] = ev
                        _emit_status(f"`{name}` necesita aprobación porque puede cambiar el sistema.")
                        self._q.put({"type": "need_approval", "data": event_payload})
                        ev.wait(timeout=60)
                        if self._approval_res.get(tid, False):
                            result = execute_tool(name, args)
                        else:
                            result = {"cancelled": True, "reason": "user_timeout", "tool": name}
                    else:
                        if dangerous and self.expert_mode:
                            try:
                                from app.agent_log import log as _alog
                                _alog("WARN", "expert_mode",
                                      f"Auto-aprobada herramienta peligrosa: {name}",
                                      {"tool": name, "args_brief": str(args)[:200]})
                            except Exception:
                                pass
                        result = execute_tool(name, args)

                    if not result.get("blocked") and not result.get("cancelled"):
                        tool_execution_count += 1

                    history.append({"role": "tool", "tool_call_id": tid,
                                    "content": json.dumps(result, ensure_ascii=False)})
                    self._q.put({"type": "tool_result",
                                 "data": {"id": tid, "result": result}})

                    # Watch mode: emit config so the server can start the screenshot loop
                    if result.get("watch_started"):
                        self._q.put({"type": "watch_config", "data": result})
                    if result.get("watch_stopped"):
                        self._q.put({"type": "watch_stop", "data": {}})

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

            # Consumo Mistral de esta sesión (visible en Actividad).
            try:
                from app import mistral_usage
                s = mistral_usage.session_summary()
                if s.get("calls"):
                    _emit_status(
                        f"Consumo Mistral (sesión): ${s['cost']:.4f} · "
                        f"{s['input']:,}+{s['output']:,} tokens · {s['calls']} llamadas"
                    )
            except Exception:
                pass

            # 💰 Dinero ahorrado usando el modelo LOCAL (vs la nube). Total acumulado.
            try:
                from app import local_usage
                ls = local_usage.session_summary()
                if ls.get("calls"):
                    tot = local_usage.get_summary("all")
                    self._q.put({"type": "savings", "data": {
                        "session_saved": round(ls["saved"], 4),
                        "total_saved": round(tot["saved_usd"], 4),
                        "total_tokens": tot["input_tokens"] + tot["output_tokens"],
                    }})
                    _emit_status(
                        f"💰 Ahorrado en local: ${ls['saved']:.4f} esta tarea · "
                        f"${tot['saved_usd']:.2f} en total ({(tot['input_tokens']+tot['output_tokens']):,} tokens gratis)"
                    )
            except Exception:
                pass

            # WEBPROD-009: coste de ESTA respuesta + acumulado del mes (todos los modelos).
            try:
                self._q.put({"type": "cost", "data": self._build_cost()})
            except Exception:
                pass

            self._q.put({"type": "done", "data": full})

            # Aviso push al móvil de que la tarea terminó (útil si te alejaste).
            # Solo cuando hubo trabajo real (herramientas) para no spamear.
            if tools_executed and not self._stop_flag:
                try:
                    from app.api import alert_sender
                    if alert_sender.cloud_configured():
                        preview = " ".join((full or "").split())[:140] or "Respuesta lista."
                        alert_sender.send_threat_alert(
                            title="✅ CyberAgent — tarea completada",
                            body=preview,
                        )
                except Exception:
                    pass
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
        from app.model_router import FAST_MODEL

        _tools_used = tools if tools is not None else TOOLS_SCHEMA

        # ── Backend Mistral (nube) ───────────────────────────────────────────
        if getattr(self, "_mistral", False):
            from app.brain import stream_mistral
            try:
                content, tool_calls, _reasoning = stream_mistral(
                    self.model, history, _tools_used,
                    emit_token=lambda d: self._q.put({"type": "token", "data": d}),
                    emit_reasoning=lambda d: self._q.put({"type": "reasoning", "data": d}),
                    should_stop=lambda: self._stop_flag,
                )
                return content, tool_calls
            except Exception as exc:
                # Fallback automático a Ollama local si Mistral falla
                self._q.put({"type": "reasoning",
                             "data": f"⚠️ Mistral falló ({exc}); sigo con el modelo local."})
                self._mistral = False
                self.model = FAST_MODEL

        # ── Backend Ollama (local) ───────────────────────────────────────────
        history = prepare_history_for_ollama(history, _tools_used)
        num_ctx = self._auto_ctx(history)
        # DEBATE-003: keep fast model always hot; power model evicts after idle period
        keep_alive = FAST_KEEP_ALIVE if self.model == FAST_MODEL else POWER_KEEP_ALIVE
        payload = {
            "model":      self.model,
            "messages":   history,
            "tools":      _tools_used,
            "stream":     True,
            "keep_alive": keep_alive,
            # Thinking nativo: OFF por defecto. En streaming+tools este abliterado
            # vuelca el razonamiento (a veces en chino) al contenido → inestable.
            # Interruptor para experimentar: CYBERAGENT_THINK=1.
            "think":      os.environ.get("CYBERAGENT_THINK", "0") == "1"
                          and any(t in (self.model or "").lower() for t in ("qwen3", "huihui")),
            "options":    {"num_ctx": num_ctx, "temperature": 0.3, "top_p": 0.95,
                           "repeat_penalty": 1.05, "top_k": 40},
        }
        _t = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=5.0)
        MAX_ATTEMPTS = 3
        RETRY_WAIT   = 25

        from app.brain import split_think, strip_lead_artifacts
        for attempt in range(MAX_ATTEMPTS):
            content    = ""
            tool_calls: dict = {}
            _think_state = False   # parser de <think> para el stream local
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
                            tdelta = msg.get("thinking", "")
                            if tdelta:   # razonamiento nativo (campo separado)
                                self._q.put({"type": "reasoning", "data": tdelta})
                            delta = msg.get("content", "")
                            if delta:
                                # Separa <think> inline (modo herramientas) → razonamiento
                                _r, _c, _think_state = split_think(delta, _think_state)
                                if _r:
                                    self._q.put({"type": "reasoning", "data": _r})
                                if _c:
                                    if not content:
                                        _c = strip_lead_artifacts(_c)
                                    if _c:
                                        content += _c
                                        self._q.put({"type": "token", "data": _c})
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
                                try:
                                    from app import local_usage
                                    local_usage.log_local(
                                        chunk.get("prompt_eval_count", 0),
                                        chunk.get("eval_count", 0),
                                        model=self.model, context="agent")
                                except Exception:
                                    pass
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
