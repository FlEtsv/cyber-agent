"""Agente no-Qt para uso en el servidor FastAPI local."""
import json, threading, queue, sys, os
import httpx

# Ajuste de path para importar módulos del proyecto
_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.tools import TOOLS_SCHEMA, execute_tool, is_dangerous
from app.ollama_client import OLLAMA_URL, OLLAMA_MODEL, SYSTEM_PROMPT


class AgentRunner:
    """Ejecuta el agente en un hilo y emite eventos SSE-style."""

    def __init__(
        self,
        messages: list,
        model: str         = OLLAMA_MODEL,
        session_trust: bool     = False,
        tool_permissions: dict  = None,
    ):
        self.messages         = messages
        self.model            = model
        self.session_trust    = session_trust
        self.tool_permissions = tool_permissions or {}
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

    # ── Internals ──────────────────────────────────────────────────────────

    def _run(self):
        try:
            system = SYSTEM_PROMPT
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

            history = [{"role": "system", "content": system}] + list(self.messages)
            full    = ""

            for iteration in range(15):
                if self._stop_flag:
                    break
                content, tool_calls = self._stream_once(history)
                full += content
                if not tool_calls:
                    break

                history.append({
                    "role":       "assistant",
                    "content":    content,
                    "tool_calls": [
                        {"function": {"name": v["name"], "arguments": v["args"]}}
                        for v in tool_calls.values()
                    ],
                })

                for idx, tc in tool_calls.items():
                    if self._stop_flag:
                        break
                    tid  = f"api_{iteration}_{idx}_{tc['name']}"
                    name = tc["name"]
                    try:
                        args = json.loads(tc["args"]) if tc["args"].strip() else {}
                    except Exception:
                        args = {}

                    dangerous = is_dangerous(name)
                    perm      = self.tool_permissions.get(name, "ask")

                    self._q.put({"type": "tool_call",
                                 "data": {"id": tid, "name": name,
                                          "args": args, "dangerous": dangerous}})

                    if perm == "block":
                        result = {"blocked": True}
                    elif dangerous and not self.session_trust and perm != "auto":
                        ev = threading.Event()
                        self._approvals[tid] = ev
                        self._q.put({"type": "need_approval",
                                     "data": {"id": tid, "name": name, "args": args}})
                        ev.wait(timeout=120)
                        if self._approval_res.get(tid, False):
                            result = execute_tool(name, args)
                        else:
                            result = {"cancelled": True}
                    else:
                        result = execute_tool(name, args)

                    history.append({"role": "tool",
                                    "content": json.dumps(result, ensure_ascii=False)})
                    self._q.put({"type": "tool_result",
                                 "data": {"id": tid, "result": result}})

            self._q.put({"type": "done", "data": full})
        except Exception as exc:
            self._q.put({"type": "error", "data": str(exc)})

    def _stream_once(self, history: list) -> tuple:
        content    = ""
        tool_calls: dict = {}
        payload = {
            "model":    self.model,
            "messages": history,
            "tools":    TOOLS_SCHEMA,
            "stream":   True,
            "options":  {"num_ctx": 8192, "temperature": 0.6, "top_p": 0.9},
        }
        with httpx.Client(timeout=180) as client:
            with client.stream("POST", OLLAMA_URL, json=payload) as resp:
                for line in resp.iter_lines():
                    if self._stop_flag or not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except Exception:
                        continue
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
                        tool_calls[idx]["args"] += fn.get("arguments", "")
                    if chunk.get("done"):
                        break
        return content, tool_calls
