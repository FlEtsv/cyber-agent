"""
Outbound WebSocket connector: PC → Cloudflare → Cloud Run relay.
Receives mobile sessions from the relay, runs AgentRunner locally,
streams results back through the relay.

NOTA: El relay está expuesto a través de Cloudflare (Proxy DNS activado).
      Cloudflare inyecta headers como CF-Connecting-IP (IP real del cliente).
"""
import asyncio, inspect, json, os, threading, time, logging
from urllib.parse import quote
import httpx
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
        self._pending: dict[str, list]   = {}   # session_id → mensajes en cola (procesar al terminar)
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

    def is_connected(self) -> bool:
        """True si hay una WebSocket activa con el relay (para el supervisor)."""
        return self._ws is not None

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
                    open_timeout=25,   # Cloud Run min-instances=0: tolera arranque en frío
                    ping_interval=20,
                    ping_timeout=60,
                ) as ws:
                    self._ws = ws
                    backoff = _BACKOFF_INIT
                    log.info(f"[relay] Conectado a {self.ws_url}/host")
                    await self._send_models(ws)
                    await self._handle_connection(ws)
            except Exception as e:
                log.error(f"[relay] Error en conexión: {e}")
                self._ws = None
                if self._running:
                    log.info(f"[relay] Reintentando en {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _send_models(self, ws):
        """Tras conectar, manda al relay la lista de modelos del PC para poblar el
        selector de la web (el relay espera type:'models'). Sin esto el selector
        del móvil aparece vacío."""
        try:
            models: list[str] = []
            try:
                async with __import__("httpx").AsyncClient(timeout=3) as c:
                    r = await c.get("http://localhost:11434/api/tags")
                    models = [m["name"] for m in r.json().get("models", [])]
            except Exception:
                pass
            await ws.send(json.dumps({
                "type": "models",
                "models": models,
                "active": OLLAMA_MODEL,
            }))
        except Exception as e:
            log.error(f"[relay] No se pudieron enviar modelos: {e}")

    async def _connection_watchdog(self, ws):
        """El relay envía un ping de aplicación cada 15s. Si dejan de llegar
        mensajes durante >45s, la conexión está muerta o MEDIO-ABIERTA (típico
        tras un redeploy del relay: el TCP sigue vivo por el balanceador pero el
        contenedor nuevo no nos tiene registrados → 'pc_online' falso para
        siempre). La cerramos para forzar la reconexión automática."""
        loop = asyncio.get_event_loop()
        ticks = 0
        try:
            while True:
                await asyncio.sleep(10)
                # a) Sin tráfico 45s → muerto/medio-abierto.
                if time.time() - self._last_rx > 45:
                    log.warning("[relay] sin tráfico del relay 45s → cierro para reconectar")
                    await self._safe_close(ws)
                    return
                # b) Cada ~30s, verifica por HTTP que la REVISIÓN ACTIVA del relay
                #    de verdad nos ve. Tras un redeploy, el WebSocket puede quedar
                #    fijado a la revisión vieja (sigue pingeando → (a) no salta)
                #    mientras la nueva no nos tiene → pc_online falso eterno.
                ticks += 1
                if ticks % 3 == 0:
                    sees = await loop.run_in_executor(None, self._relay_sees_us)
                    if sees is False:
                        log.warning("[relay] la revisión activa no nos ve → reconectando")
                        await self._safe_close(ws)
                        return
        except asyncio.CancelledError:
            pass

    async def _safe_close(self, ws):
        try:
            await ws.close()
        except Exception:
            pass

    def _relay_sees_us(self):
        """GET HTTP a la revisión activa del relay: ¿nos tiene como host? Devuelve
        True/False, o None si no es concluyente (cold start/error) para no forzar
        reconexiones en falso."""
        try:
            r = httpx.get(f"{self.http_url}/api/status", timeout=6.0)
            if r.status_code != 200:
                return None
            return bool(r.json().get("pc_online", False))
        except Exception:
            return None

    async def _handle_connection(self, ws):
        """Main loop: receive messages from relay, spawn runners."""
        self._last_rx = time.time()
        watchdog = asyncio.create_task(self._connection_watchdog(ws))
        try:
            async for raw in ws:
                self._last_rx = time.time()   # cualquier mensaje (incl. ping) = conexión viva
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                if msg_type == "message":
                    # La web/relay envía type:"message". Lo corremos en una tarea
                    # para NO bloquear el bucle de recepción (pings y siguientes
                    # mensajes) mientras el agente trabaja.
                    sid = msg.get("session_id", "")
                    if sid in self._runners:
                        # Ya hay una ejecución en curso: encola la instrucción para
                        # procesarla al terminar (aceptar más instrucciones aunque
                        # esté procesando, como un asistente de verdad).
                        self._pending.setdefault(sid, []).append(msg)
                        pos = len(self._pending[sid])
                        await ws.send(json.dumps({
                            "type": "status", "session_id": sid,
                            "data": f"📥 Instrucción en cola ({pos}) — la haré al terminar lo actual."}))
                    else:
                        asyncio.create_task(self._handle_message(ws, msg))
                elif msg_type == "stop":
                    r = self._runners.get(msg.get("session_id", ""))
                    if r:
                        r.stop()
                elif msg_type == "approve":
                    # Aprobación de herramienta peligrosa desde el móvil. Sin esto,
                    # el runner se quedaba esperando para siempre → la acción fallaba.
                    sid = msg.get("session_id", "")
                    r = self._runners.get(sid)
                    if r is None and len(self._runners) == 1:
                        r = next(iter(self._runners.values()))
                    if r:
                        r.approve(msg.get("tool_id", ""), bool(msg.get("approved", False)))
                elif msg_type in ("watch_start", "watch_stop"):
                    # El modo vigilancia (captura de pantalla en bucle) solo existe en
                    # la sesión local; en remoto lo ignoramos sin romper el bucle.
                    if msg_type == "watch_start":
                        await ws.send(json.dumps({
                            "type": "status", "session_id": msg.get("session_id", ""),
                            "data": "El modo vigilancia solo está disponible en el PC."}))
                elif msg_type == "session:new":
                    await self._handle_new_session(ws, msg)
                elif msg_type == "session:resume":
                    await self._handle_resume_session(ws, msg)
                elif msg_type == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                elif msg_type == "generate_image":
                    asyncio.create_task(self._handle_generate_image(ws, msg))
                elif msg_type and msg_type.startswith("workspace:"):
                    await self._handle_workspace(ws, msg)
        except Exception as e:
            log.error(f"[relay] Error en conexión: {e}")
        finally:
            watchdog.cancel()
            self._stop_all_runners()

    async def _handle_generate_image(self, ws, msg: dict):
        """WEBPROD-005: crea una imagen con FLUX (Mistral Studio) de forma directa,
        sin depender de que el modelo decida llamarla. Devuelve burbuja + archivo."""
        session_id = msg.get("session_id", "")
        prompt = (msg.get("prompt") or "").strip()
        if not session_id or not prompt:
            return

        async def _send(obj):
            try:
                await ws.send(json.dumps({**obj, "session_id": session_id}))
            except Exception:
                pass

        await _send({"type": "status", "data": "🎨 Generando imagen…"})
        try:
            from app.mistral_studio import available, run
            if not available():
                await _send({"type": "token",
                             "data": "No puedo crear imágenes: falta MISTRAL_API_KEY en el PC."})
                await _send({"type": "done"})
                return
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None, lambda: run(prompt, connectors=["image_generation"]))
        except Exception as e:
            await _send({"type": "token", "data": f"Error generando la imagen: {e}"})
            await _send({"type": "done"})
            return

        files = res.get("files") or [] if isinstance(res, dict) else []
        if not files:
            txt = (res or {}).get("text") or "No se generó ninguna imagen."
            await _send({"type": "token", "data": txt})
            await _send({"type": "done"})
            return

        # Nombre robusto en Windows y POSIX (rutas con \ o /).
        import os as _os
        def _fname(f):
            return _os.path.basename(f.get("path", "")) or "imagen.png"
        # Registra cada imagen como archivo de la conversación y arma la respuesta.
        try:
            from app import database as db
            for f in files:
                db.register_file(f.get("path", ""), name=_fname(f),
                                 url=f.get("url"), conversation_id=msg.get("conversation_id"),
                                 folder_id=msg.get("folder_id"), kind="image")
        except Exception:
            pass
        md = f"🎨 Imagen generada para: *{prompt}*\n\n" + "\n".join(
            f"![imagen]({f.get('url')})" for f in files if f.get("url"))
        await _send({"type": "token", "data": md})
        await _send({"type": "files", "data": [
            {"name": _fname(f), "url": f.get("url"), "kind": "image"} for f in files]})
        await _send({"type": "done"})

    async def _handle_workspace(self, ws, msg: dict):
        """CRUD de carpetas/conversaciones/archivos del workspace (web→relay→host→SQLite).
        Usa el dispatch compartido (app/workspace.py). google_connect bloquea (abre
        el navegador) → se ejecuta en un hilo."""
        from app import workspace as _ws
        action = (msg.get("type") or "").split(":", 1)[1]
        rid = msg.get("req_id")
        if action == "google_connect":
            from app import google_suite as _g
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, _g.google_connect)
        else:
            data = _ws.handle_sync(action, msg)
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
        images = msg.get("images") or []
        if not session_id or (not content and not images):
            return

        # WEBPROD-013/006: las imágenes adjuntas desde la web SÍ se procesan ahora.
        # Se interpretan (visión local o Pixtral) y se inyectan en el prompt.
        if images:
            try:
                await ws.send(json.dumps({"type": "status", "session_id": session_id,
                                          "data": f"Analizando {len(images)} imagen(es)…"}))
            except Exception:
                pass
            try:
                from app.vision import describe_images
                content = (content + await describe_images(images)).strip()
            except Exception as e:
                content = (content + f"\n\n[imagen adjunta — error de visión: {e}]").strip()

        # WEBPROD-014/011: adjuntos NO-imagen (scripts/docs/pdf/csv…) → contenido en el
        # prompt + registro como archivo de la conversación.
        files = msg.get("files") or []
        if files:
            try:
                from app.attachments import process_attachments
                content = (content + process_attachments(
                    files,
                    conversation_id=msg.get("conversation_id"),
                    folder_id=msg.get("folder_id"))).strip()
            except Exception as e:
                content = (content + f"\n\n[archivo adjunto — error: {e}]").strip()

        if not content:
            return

        # Contexto: si el cliente envía su historial (sobrevive reconexiones y
        # reinicios del host), lo usamos como fuente de verdad; si no, el estado local.
        client_hist = msg.get("history")
        if isinstance(client_hist, list) and client_hist:
            conv = [m for m in client_hist
                    if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")][-40:]
            self._convs[session_id] = conv
        else:
            conv = self._convs.setdefault(session_id, [])
        # No dupliques el turno: si el historial del cliente ya termina con este
        # mismo mensaje de usuario (pasa al escalar/reintentar), no lo añadas otra vez.
        last = conv[-1] if conv else None
        if not (last and last.get("role") == "user" and last.get("content") == content):
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

        # ¿Hay instrucciones encoladas para esta sesión? Procesa la siguiente.
        pend = self._pending.get(session_id)
        if pend:
            nxt = pend.pop(0)
            if not pend:
                self._pending.pop(session_id, None)
            # El history del cliente se capturó antes de esta respuesta → obsoleto.
            # Lo quitamos para que use la conversación acumulada (ya con la réplica).
            nxt.pop("history", None)
            asyncio.create_task(self._handle_message(ws, nxt))

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


def relay_status() -> dict:
    """Estado del conector del relay para el supervisor de Conexión."""
    configured = bool(os.environ.get("RELAY_URL") and os.environ.get("RELAY_HOST_SECRET"))
    c = _connector
    return {
        "configured": configured,
        "thread_alive": bool(c and c._running),
        "connected": bool(c and c.is_connected()),
    }
