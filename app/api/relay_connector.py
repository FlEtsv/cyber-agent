"""
Outbound WebSocket connector: PC → Cloudflare → Cloud Run relay.
Receives mobile sessions from the relay, runs AgentRunner locally,
streams results back through the relay.

NOTA: El relay está expuesto a través de Cloudflare (Proxy DNS activado).
      Cloudflare inyecta headers como CF-Connecting-IP (IP real del cliente).
"""
import asyncio, inspect, json, os, threading, logging
from urllib.parse import quote
import websockets

from app.ollama_client import OLLAMA_MODEL

# websockets >= 14 renombró el parámetro  extra_headers -> additional_headers.
# Detectamos el nombre correcto para conectar con cualquier versión instalada
# (con websockets 16.0 usar extra_headers lanzaba TypeError y el host NUNCA
# llegaba a conectar con el relay).
try:
    _WS_HEADERS_KW = (
        "additional_headers"
        if "additional_headers" in inspect.signature(websockets.connect).parameters
        else "extra_headers"
    )
except (ValueError, TypeError):
    _WS_HEADERS_KW = "additional_headers"

log = logging.getLogger("relay_connector")

_BACKOFF_INIT = 5    # seconds before first retry
_BACKOFF_MAX  = 60   # cap for exponential backoff
_ANNOUNCE_INTERVAL = 20


def _get_client_ip_from_headers(headers: dict) -> str:
    """
    Extrae la IP real del cliente desde headers de Cloudflare.
    Cloudflare inyecta CF-Connecting-IP con la IP del cliente original.
    """
    # Header de Cloudflare: CF-Connecting-IP (ej: "203.0.113.195")
    cf_ip = headers.get("CF-Connecting-IP", "")
    if cf_ip:
        return cf_ip
    # Fallback: X-Forwarded-For (puede estar en Cloud Run)
    forwarded_for = headers.get("X-Forwarded-For", "")
    if forwarded_for:
        # X-Forwarded-For puede ser una lista de IPs: "client, proxy1, proxy2"
        return forwarded_for.split(",")[0].strip()
    return "unknown"


def _requested_model_from_message(msg: dict) -> str:
    raw = msg.get("model")
    if not isinstance(raw, str):
        return "auto"
    model = raw.strip()
    return model or "auto"


class RelayConnector:
    def __init__(self, relay_url: str, host_secret: str):
        # relay_url: wss://relay.cyberagent.cloud (no trailing slash)
        self.ws_url     = relay_url.rstrip("/").replace("https://", "wss://").replace("http://", "ws://")
        self.http_url   = relay_url.rstrip("/").replace("wss://", "https://").replace("ws://", "http://")
        self.host_secret = host_secret
        self._runners: dict[str, object] = {}   # session_id → AgentRunner
        self._convs:   dict[str, list]   = {}   # session_id → conversation history
        self._ws       = None
        self._running  = False
        self._use_cloudflare_headers = os.environ.get("USE_CLOUDFLARE_HEADERS", "True").lower() == "true"

    def start(self):
        """Start in a background thread."""
        self._running = True
        t = threading.Thread(target=self._thread, daemon=True, name="relay-connector")
        t.start()
        return t

    def stop(self):
        self._running = False

    # ── Background thread ─────────────────────────────────────────────────────

    def _thread(self):
        asyncio.run(self._async_run())

    def _stop_all_runners(self) -> None:
        """Stop and discard all active runners (called on WS disconnect)."""
        for runner in list(self._runners.values()):
            try:
                runner.stop()
            except Exception:
                pass
        self._runners.clear()

    async def _async_run(self):
        backoff = _BACKOFF_INIT
        while self._running:
            try:
                # El relay autentica el host por query param (?secret=...);
                # mandamos también el header por compatibilidad futura.
                async with websockets.connect(
                    f"{self.ws_url}/host?secret={quote(self.host_secret, safe='')}",
                    **{_WS_HEADERS_KW: {"X-Host-Secret": self.host_secret}},
                    ping_interval=20,
                    ping_timeout=60,
                ) as ws:
                    self._ws = ws
                    backoff = _BACKOFF_INIT
                    log.info(f"[relay] Conectado a {self.ws_url}/host")
                    await self._handle_connection(ws)
            except Exception as e:
                log.error(f"[relay] Error en conexión: {e}")
                self._ws = None
                if self._running:
                    log.info(f"[relay] Reintentando en {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _handle_connection(self, ws):
        """Main loop: receive messages from relay, spawn runners."""
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                if msg_type == "message":
                    # La web/relay envía type:"message". Lo corremos en una tarea
                    # para NO bloquear el bucle de recepción (pings y siguientes
                    # mensajes) mientras el agente trabaja.
                    asyncio.create_task(self._handle_message(ws, msg))
                elif msg_type == "stop":
                    r = self._runners.get(msg.get("session_id", ""))
                    if r:
                        r.stop()
                elif msg_type == "session:new":
                    await self._handle_new_session(ws, msg)
                elif msg_type == "session:resume":
                    await self._handle_resume_session(ws, msg)
                elif msg_type == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                elif msg_type and msg_type.startswith("workspace:"):
                    await self._handle_workspace(ws, msg)
        except Exception as e:
            log.error(f"[relay] Error en conexión: {e}")
        finally:
            self._stop_all_runners()

    async def _handle_workspace(self, ws, msg: dict):
        """CRUD de carpetas/conversaciones del workspace (web→relay→host→SQLite).
        El backend (SQLite del PC) es la fuente de verdad sincronizada."""
        from app import database as db
        action = (msg.get("type") or "").split(":", 1)[1]
        rid = msg.get("req_id")
        data: dict = {}
        try:
            if action == "get":
                data = {"folders": db.get_folders(), "conversations": db.get_conversations()}
            elif action == "files_get":
                data = {"files": db.get_files()}
            elif action == "folder_create":
                data = {"id": db.create_folder(
                    msg.get("name", ""), msg.get("parent_id"), msg.get("color"),
                    msg.get("context", ""), msg.get("default_model"))}
            elif action == "folder_update":
                db.update_folder(msg["id"], **{k: msg[k] for k in
                    ("name", "parent_id", "color", "context", "default_model", "position")
                    if k in msg})
                data = {"ok": True}
            elif action == "folder_delete":
                db.delete_folder(msg["id"])
                data = {"ok": True}
            elif action == "conv_move":
                db.move_conversation(msg["conv_id"], msg.get("folder_id"))
                data = {"ok": True}
            elif action == "conv_color":
                db.set_conversation_color(msg["conv_id"], msg.get("color"))
                data = {"ok": True}
            else:
                data = {"error": f"acción desconocida: {action}"}
        except Exception as e:
            data = {"error": f"{type(e).__name__}: {e}"}
        try:
            # session_id obligatorio: el relay reenvía al cliente correcto por él.
            await ws.send(json.dumps({"type": "workspace:result",
                                      "session_id": msg.get("session_id"),
                                      "req_id": rid, "action": action, **data}))
        except Exception:
            pass

    async def _handle_message(self, ws, msg: dict):
        """Procesa un mensaje del usuario (web→relay→host): corre el agente y
        devuelve el stream de eventos etiquetados con session_id."""
        session_id = msg.get("session_id", "")
        content = (msg.get("content") or "").strip()
        if not session_id or not content:
            return

        # Contexto: si el cliente envía su historial (sobrevive reconexiones y
        # reinicios del host), lo usamos como fuente de verdad; si no, el estado local.
        client_hist = msg.get("history")
        if isinstance(client_hist, list) and client_hist:
            conv = [m for m in client_hist
                    if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")][-40:]
            conv.append({"role": "user", "content": content})
            self._convs[session_id] = conv
        else:
            conv = self._convs.setdefault(session_id, [])
            conv.append({"role": "user", "content": content})
        conv_trimmed = conv[-40:]
        requested_model = _requested_model_from_message(msg)
        try:
            from app.agent_log import log as _log
            _log("INFO", "relay", "Modelo solicitado desde relay",
                 {"model": requested_model, "session": session_id})
        except Exception:
            pass

        try:
            from app.api.agent_runner import AgentRunner
            runner = AgentRunner(
                messages         = list(conv_trimmed),
                model            = requested_model,
                session_trust    = bool(msg.get("session_trust", False)),
                tool_permissions = msg.get("permissions", {}) or {},
                device_context   = "móvil (relay)",
                expert_mode      = False,   # nunca auto-aprobar peligrosas en remoto
                folder_id        = msg.get("folder_id"),
            )
        except Exception as e:
            try:
                await ws.send(json.dumps({"type": "error",
                                          "data": f"Error iniciando agente: {e}",
                                          "session_id": session_id}))
            except Exception:
                pass
            return

        self._runners[session_id] = runner
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        _SENTINEL = object()
        full: list[str] = []

        def _run():
            try:
                for evt in runner.events():
                    loop.call_soon_threadsafe(q.put_nowait, evt)
            except Exception as e:
                loop.call_soon_threadsafe(q.put_nowait, {"type": "error", "data": str(e)})
            finally:
                loop.call_soon_threadsafe(q.put_nowait, _SENTINEL)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            evt = await q.get()
            if evt is _SENTINEL:
                break
            try:
                await ws.send(json.dumps({**evt, "session_id": session_id}))
            except Exception:
                runner.stop()
                break
            if evt.get("type") == "done":
                full.append(evt.get("data", ""))

        if full:
            conv.append({"role": "assistant", "content": full[0]})
        self._runners.pop(session_id, None)

    async def _handle_new_session(self, ws, msg: dict):
        session_id = msg.get("session_id", "")
        if not session_id:
            return

        # Extraer IP real del cliente si Cloudflare está activado
        client_ip = "unknown"
        if self._use_cloudflare_headers and hasattr(ws, "request_headers"):
            client_ip = _get_client_ip_from_headers(ws.request_headers)

        log.info(f"[relay] Nueva sesión: {session_id} (IP: {client_ip})")

        # Inicializar conversación
        self._convs[session_id] = []

        # Crear runner
        try:
            from app.agent_runner import AgentRunner
            from app.tools import execute_tool
            from app.database import get_conversation, save_conversation

            # Cargar historial si existe
            conv = get_conversation(session_id)
            if conv:
                self._convs[session_id] = conv

            model = _requested_model_from_message(msg)
            runner = AgentRunner(
                session_id=session_id,
                model=model,
                conversation=self._convs[session_id],
                execute_tool=execute_tool,
                client_ip=client_ip,  # Pasar IP real al runner
            )
            self._runners[session_id] = runner

            # Enviar confirmación
            await ws.send(json.dumps({
                "type": "session:ready",
                "session_id": session_id,
                "model": model,
            }))
        except Exception:
            runner.stop()
            self._runners.pop(session_id, None)
            return

        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        full = []
        _SENTINEL = object()

        def _run():
            try:
                for evt in runner.events():
                    loop.call_soon_threadsafe(q.put_nowait, evt)
            except Exception as e:
                loop.call_soon_threadsafe(
                    q.put_nowait, {"type": "error", "data": str(e)}
                )
            finally:
                loop.call_soon_threadsafe(q.put_nowait, _SENTINEL)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            evt = await q.get()
            if evt is _SENTINEL:
                break
            try:
                await ws.send(json.dumps({**evt, "session_id": session_id}))
            except Exception:
                runner.stop()
                break
            if evt["type"] in ("done", "error"):
                if evt["type"] == "done":
                    full.append(evt.get("data", ""))
                break

        if full:
            self._convs[session_id].append({"role": "assistant", "content": full[0]})

        self._runners.pop(session_id, None)

    async def _handle_resume_session(self, ws, msg: dict):
        session_id = msg.get("session_id", "")
        if not session_id:
            return

        # Extraer IP real del cliente si Cloudflare está activado
        client_ip = "unknown"
        if self._use_cloudflare_headers and hasattr(ws, "request_headers"):
            client_ip = _get_client_ip_from_headers(ws.request_headers)

        log.info(f"[relay] Reanudando sesión: {session_id} (IP: {client_ip})")

        try:
            from app.agent_runner import AgentRunner
            from app.tools import execute_tool
            from app.database import get_conversation

            conv = get_conversation(session_id)
            if not conv:
                await ws.send(json.dumps({
                    "type": "error",
                    "data": f"No se encontró la conversación para {session_id}",
                    "session_id": session_id,
                }))
                return

            self._convs[session_id] = conv

            runner = AgentRunner(
                session_id=session_id,
                model=_requested_model_from_message(msg),
                conversation=conv,
                execute_tool=execute_tool,
                client_ip=client_ip,  # Pasar IP real al runner
            )
            self._runners[session_id] = runner

            await ws.send(json.dumps({
                "type": "session:ready",
                "session_id": session_id,
            }))
        except Exception:
            runner.stop()
            self._runners.pop(session_id, None)
            return

        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        full = []
        _SENTINEL = object()

        def _run():
            try:
                for evt in runner.events():
                    loop.call_soon_threadsafe(q.put_nowait, evt)
            except Exception as e:
                loop.call_soon_threadsafe(
                    q.put_nowait, {"type": "error", "data": str(e)}
                )
            finally:
                loop.call_soon_threadsafe(q.put_nowait, _SENTINEL)

        threading.Thread(target=_run, daemon=True).start()

        while True:
            evt = await q.get()
            if evt is _SENTINEL:
                break
            try:
                await ws.send(json.dumps({**evt, "session_id": session_id}))
            except Exception:
                runner.stop()
                break
            if evt["type"] in ("done", "error"):
                if evt["type"] == "done":
                    full.append(evt.get("data", ""))
                break

        if full:
            self._convs[session_id].append({"role": "assistant", "content": full[0]})

        self._runners.pop(session_id, None)


# ── Module-level singleton ─────────────────────────────────────────────────────

_connector: RelayConnector | None = None

def start_relay_connector():
    global _connector
    relay_url   = os.environ.get("RELAY_URL", "")
    host_secret = os.environ.get("RELAY_HOST_SECRET", "")
    if not relay_url or not host_secret:
        return None
    _connector = RelayConnector(relay_url, host_secret)
    _connector.start()
    log.info(f"[relay] Conector iniciado → {relay_url}")
    return _connector
