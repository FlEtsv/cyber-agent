"""
Outbound WebSocket connector: PC → Cloud Run relay.
Receives mobile sessions from the relay, runs AgentRunner locally,
streams results back through the relay.
"""
import asyncio, json, os, threading, logging
import websockets

from app.ollama_client import OLLAMA_MODEL

log = logging.getLogger("relay_connector")

_BACKOFF_INIT = 5    # seconds before first retry
_BACKOFF_MAX  = 60   # cap for exponential backoff
_ANNOUNCE_INTERVAL = 20


class RelayConnector:
    def __init__(self, relay_url: str, host_secret: str):
        # relay_url: wss://xxx.run.app  (no trailing slash)
        self.ws_url     = relay_url.rstrip("/").replace("https://", "wss://").replace("http://", "ws://")
        self.http_url   = relay_url.rstrip("/").replace("wss://", "https://").replace("ws://", "http://")
        self.host_secret = host_secret
        self._runners: dict[str, object] = {}   # session_id → AgentRunner
        self._convs:   dict[str, list]   = {}   # session_id → conversation history
        self._ws       = None
        self._running  = False

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
        url = f"{self.ws_url}/host?secret={self.host_secret}"
        backoff = _BACKOFF_INIT
        while self._running:
            connected = False
            try:
                log.info(f"[relay] Conectando a {self.ws_url}/host")
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self._ws = ws
                    connected = True
                    log.info("[relay] Conectado al relay")
                    await self._handle(ws)
            except Exception as e:
                log.warning(f"[relay] Desconectado: {e}. Reintentando en {backoff}s…")
            finally:
                self._ws = None
                self._stop_all_runners()
            if not self._running:
                break
            await asyncio.sleep(backoff)
            backoff = _BACKOFF_INIT if connected else min(backoff * 2, _BACKOFF_MAX)

    async def _announce_models(self, ws) -> bool:
        """RELAY-BE-001: push current model list to relay right after connecting."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            models = []
        from app.model_router import FAST_MODEL, POWER_MODEL
        active = FAST_MODEL  # fast model is always warm at startup
        try:
            await ws.send(json.dumps({"type": "models", "models": models, "active": active}))
            return True
        except Exception:
            return False

    async def _remote_reports_pc_online(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.http_url}/api/status", params={"t": str(os.getpid())})
            if r.status_code != 200:
                return True
            data = r.json()
            return bool(data.get("pc_online"))
        except Exception:
            return True

    async def _announce_loop(self, ws):
        while self._running:
            await asyncio.sleep(_ANNOUNCE_INTERVAL)
            if not await self._announce_models(ws):
                try:
                    await ws.close()
                except Exception:
                    pass
                return
            if not await self._remote_reports_pc_online():
                log.warning("[relay] La revision activa no ve el PC online; forzando reconexion")
                try:
                    await ws.close()
                except Exception:
                    pass
                return

    async def _handle(self, ws):
        # Announce model list immediately on connect
        if not await self._announce_models(ws):
            return
        announce_task = asyncio.create_task(self._announce_loop(ws))

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue

                session_id = msg.get("session_id")
                t = msg.get("type")

                # RELAY-BE-003: relay pings us to confirm we're alive
                if t == "ping":
                    try:
                        await ws.send(json.dumps({"type": "pong"}))
                    except Exception:
                        break
                    if not await self._announce_models(ws):
                        break
                    continue

                if t == "message":
                    asyncio.create_task(self._on_message(ws, session_id, msg))
                elif t == "approve":
                    runner = self._runners.get(session_id)
                    if runner:
                        runner.approve(msg.get("tool_id", ""), bool(msg.get("approved", False)))
                elif t == "stop":
                    runner = self._runners.get(session_id)
                    if runner:
                        runner.stop()
                elif t == "session_closed":
                    runner = self._runners.pop(session_id, None)
                    if runner:
                        runner.stop()
                    self._convs.pop(session_id, None)
        finally:
            announce_task.cancel()

    async def _on_message(self, ws, session_id: str, msg: dict):
        from app.api.agent_runner import AgentRunner

        # Guard: stop concurrent coroutines for the same session
        if session_id in self._runners:
            return

        content    = msg.get("content", "").strip()
        device_ctx = msg.get("device", "móvil (relay)")

        if session_id not in self._convs:
            self._convs[session_id] = []

        self._convs[session_id].append({"role": "user", "content": content})
        self._convs[session_id] = self._convs[session_id][-40:]

        runner = AgentRunner(
            messages         = list(self._convs[session_id]),
            session_trust    = msg.get("session_trust", False),
            tool_permissions = msg.get("permissions", {}),
            device_context   = device_ctx,
        )
        self._runners[session_id] = runner

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
