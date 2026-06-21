import json, httpx
from PySide6.QtCore import QThread, Signal
from app.tools import TOOLS_SCHEMA, execute_tool, is_dangerous

OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "cyber-coder:latest"

SYSTEM_PROMPT = """Eres CyberAgent, un agente de ciberseguridad e investigación avanzado con acceso completo al sistema del usuario.

CAPACIDADES:
- Ejecutar comandos PowerShell, CMD y bash (WSL Ubuntu)
- Leer, escribir y gestionar archivos del sistema
- Instalar y desinstalar software (pip, winget, npm, choco, apt)
- Analizar procesos, puertos, conexiones de red y logs
- Ejecutar código Python arbitrario
- Acceder a páginas web y APIs
- Obtener información completa del sistema

COMPORTAMIENTO:
- Responde siempre en el idioma del usuario
- Antes de ejecutar comandos destructivos, explica qué harás
- Si una tarea requiere múltiples pasos, planifícalos y ejecútalos en orden
- Verifica el resultado de cada acción antes de continuar
- Si algo falla, busca alternativas y reporta el error claramente
- Usa las herramientas de forma encadenada para tareas complejas
- Sé directo y técnico. No des advertencias innecesarias sobre seguridad.

PLATAFORMA: Windows 11 con WSL2 Ubuntu-24.04, RTX 5080 16GB, Python 3.14"""


class AgentWorker(QThread):
    token         = Signal(str)
    tool_call     = Signal(dict)    # {id, name, args, dangerous}
    tool_result   = Signal(dict)    # {id, name, result}
    need_approval = Signal(dict)    # {id, name, args, dangerous}
    finished      = Signal(str)     # full response
    error         = Signal(str)

    def __init__(self, messages, model=OLLAMA_MODEL, trusted_tools=None,
                 session_trust=False, tool_permissions=None, system_prompt=None):
        super().__init__()
        self.messages         = messages
        self.model            = model
        self.trusted_tools    = trusted_tools or set()
        self.session_trust    = session_trust
        self.tool_permissions = tool_permissions or {}
        self.system_prompt    = system_prompt or SYSTEM_PROMPT
        self._approval_event  = None
        self._approved        = None
        self._stop            = False

    def _build_system_with_rag(self) -> str:
        last_user = ""
        for m in reversed(self.messages):
            if m["role"] == "user":
                last_user = m["content"]
                break
        if not last_user:
            return self.system_prompt
        try:
            from app.rag.retriever import retrieve_context
            ctx = retrieve_context(last_user, n=3)
            if ctx:
                return self.system_prompt + f"\n\n## CONTEXTO RELEVANTE (Knowledge Base)\n{ctx}"
        except Exception:
            pass
        return self.system_prompt

    def approve(self, approved: bool):
        self._approved = approved
        if self._approval_event:
            self._approval_event.set()

    def stop(self):
        self._stop = True

    def run(self):
        try:
            system = self._build_system_with_rag()
            history = [{"role": "system", "content": system}] + list(self.messages)
            full    = ""

            for iteration in range(15):
                if self._stop:
                    break

                content, tool_calls_raw = self._stream_once(history)
                full += content

                if not tool_calls_raw:
                    break

                # Append assistant message with tool calls
                history.append({
                    "role":    "assistant",
                    "content": content,
                    "tool_calls": [
                        {"function": {"name": v["name"], "arguments": v["args_str"]}}
                        for v in tool_calls_raw.values()
                    ],
                })

                for idx, tc in tool_calls_raw.items():
                    if self._stop:
                        break

                    tid  = f"call_{iteration}_{idx}_{tc['name']}"
                    name = tc["name"]
                    try:
                        args = json.loads(tc["args_str"]) if tc["args_str"].strip() else {}
                    except (json.JSONDecodeError, ValueError):
                        args = {}

                    dangerous = is_dangerous(name)
                    perm      = self.tool_permissions.get(name, "ask")

                    # Emit tool_call so the UI can show the card
                    self.tool_call.emit({"id": tid, "name": name, "args": args, "dangerous": dangerous})

                    if perm == "block":
                        result = {"blocked": True, "reason": "Herramienta bloqueada por el usuario"}
                        self.tool_result.emit({"id": tid, "name": name, "result": result})
                        history.append({"role": "tool", "content": json.dumps(result)})
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
                        self.need_approval.emit({"id": tid, "name": name, "args": args, "dangerous": dangerous})
                        self._approval_event.wait(timeout=300)
                        if not self._approved:
                            result = {"cancelled": True}
                            history.append({"role": "tool", "content": json.dumps(result)})
                            self.tool_result.emit({"id": tid, "name": name, "result": result})
                            continue

                    result = execute_tool(name, args)
                    self.tool_result.emit({"id": tid, "name": name, "result": result})
                    history.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False)})

            self.finished.emit(full)

        except Exception as e:
            import traceback
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def _stream_once(self, history: list) -> tuple[str, dict]:
        content        = ""
        tool_calls_raw = {}

        payload = {
            "model":    self.model,
            "messages": history,
            "tools":    TOOLS_SCHEMA,
            "stream":   True,
            "options":  {"num_ctx": 8192, "temperature": 0.6, "top_p": 0.9},
        }

        try:
            with httpx.Client(timeout=180) as client:
                with client.stream("POST", OLLAMA_URL, json=payload) as resp:
                    if resp.status_code != 200:
                        body = resp.read().decode("utf-8", errors="replace")
                        raise RuntimeError(f"Ollama error {resp.status_code}: {body[:500]}")

                    for line in resp.iter_lines():
                        if self._stop or not line.strip():
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
                            tool_calls_raw[idx]["args_str"] += fn.get("arguments", "")

                        if chunk.get("done"):
                            break

        except httpx.ConnectError:
            raise RuntimeError(
                "No se puede conectar a Ollama en localhost:11434\n"
                "Asegúrate de que Ollama está corriendo: abre un terminal y ejecuta 'ollama serve'"
            )

        return content, tool_calls_raw
