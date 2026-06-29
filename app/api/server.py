"""CyberAgent Web Server — FastAPI + WebSocket + PWA + Auth."""
import asyncio, json, os, threading, base64
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Response, Cookie
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import httpx

from app.auth import (
    is_setup_done, setup_user, verify_login,
    create_token, verify_token, get_totp_qr_svg,
)

WEB_DIR = Path(__file__).parent.parent / "web"          # runtime local (served/)
# La web es un producto unico en apps/web; tanto el PC como el relay la consumen.
WEB_PRODUCT = Path(__file__).parent.parent.parent / "apps" / "web"
if not (WEB_PRODUCT / "index.html").exists():
    WEB_PRODUCT = WEB_DIR  # fallback de seguridad


@asynccontextmanager
async def _lifespan(app_):
    # DEBATE-003: pre-warm fast model in background so first response is instant
    def _warm():
        try:
            from app.ollama_client import warm_fast_model, _autostart_ollama
            if _autostart_ollama():
                warm_fast_model()
        except Exception:
            pass
    threading.Thread(target=_warm, daemon=True).start()
    yield


app = FastAPI(docs_url=None, redoc_url=None, lifespan=_lifespan)

_CORS_LOCAL = frozenset(["http://localhost:8765", "http://127.0.0.1:8765"])

class _DynamicCORS(BaseHTTPMiddleware):
    """CORS middleware that reads CYBERAGENT_CLOUD_URL on every request."""
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        cloud  = os.environ.get("CYBERAGENT_CLOUD_URL", "")
        allowed = _CORS_LOCAL | ({cloud} if cloud else set())

        if request.method == "OPTIONS":
            if origin in allowed:
                return Response(
                    status_code=204,
                    headers={
                        "Access-Control-Allow-Origin":      origin,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods":     "*",
                        "Access-Control-Allow-Headers":     "*",
                        "Access-Control-Max-Age":           "600",
                    },
                )
            return Response(status_code=403)

        resp = await call_next(request)
        if origin in allowed:
            resp.headers["Access-Control-Allow-Origin"]      = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
        return resp

app.add_middleware(_DynamicCORS)


@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def _generic_exc(request: Request, exc: Exception):
    try:
        from app.agent_log import log_exception as _lex
        _lex("server", f"{type(exc).__name__} @ {request.method} {request.url.path}")
    except Exception:
        pass
    return JSONResponse({"error": "Error interno del servidor"}, status_code=500)


# /static -> producto web (apps/web es plano, igual que sirve el relay)
_STATIC = (WEB_PRODUCT / "static") if (WEB_PRODUCT / "static").exists() else WEB_PRODUCT
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

# Archivos generados por el agente (documentos, imágenes) servidos por URL pública.
_SERVED = WEB_DIR / "served"
_SERVED.mkdir(parents=True, exist_ok=True)
app.mount("/served", StaticFiles(directory=str(_SERVED)), name="served")


@app.get("/download/{name:path}")
def download_file(name: str):
    """Descarga forzada (Content-Disposition: attachment) de un archivo servido.
    Para PDFs y demás: /served/x.pdf lo abre en el navegador; /download/x.pdf lo baja."""
    # Resuelve dentro de _SERVED evitando path traversal.
    target = (_SERVED / name).resolve()
    try:
        target.relative_to(_SERVED.resolve())
    except ValueError:
        return JSONResponse({"error": "ruta no permitida"}, status_code=400)
    if not target.is_file():
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    return FileResponse(str(target), filename=target.name,
                        media_type="application/octet-stream")


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _get_token(request: Request) -> str | None:
    return request.cookies.get("ca_token")

def _auth_ok(request: Request) -> bool:
    token = _get_token(request)
    return bool(token and verify_token(token))


# ── Auth API ──────────────────────────────────────────────────────────────────

@app.get("/api/auth/status")
async def auth_status():
    return {"setup_done": is_setup_done()}

@app.post("/api/auth/setup")
async def auth_setup(req: Request):
    body = await req.json()
    email    = body.get("email", "").strip()
    password = body.get("password", "")
    if not email or len(password) < 8:
        return JSONResponse({"ok": False, "error": "Datos inválidos"}, status_code=400)
    if is_setup_done():
        return JSONResponse({"ok": False, "error": "Ya configurado"}, status_code=400)
    try:
        qr_svg = _setup_and_get_qr(email, password)
        return {"ok": True, "qr_svg": qr_svg}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

def _setup_and_get_qr(email: str, password: str) -> str:
    setup_user(email, password)
    return get_totp_qr_svg(email)

@app.post("/api/auth/login")
async def auth_login(req: Request):
    body  = await req.json()
    email = body.get("email", "").strip()
    pw    = body.get("password", "")
    totp  = body.get("totp", "").strip().replace(" ", "")

    if not verify_login(email, pw, totp):
        return JSONResponse({"ok": False, "error": "Credenciales incorrectas"}, status_code=401)

    token = create_token(email)
    resp  = JSONResponse({"ok": True})
    is_https = req.url.scheme == "https"
    resp.set_cookie(
        "ca_token", token,
        httponly=True, samesite="lax", secure=is_https,
        max_age=72 * 3600,
    )
    return resp

@app.post("/api/auth/logout")
async def auth_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("ca_token")
    return resp


# ── PWA static files (auth-gated) ─────────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    if not _auth_ok(request):
        return RedirectResponse("/login")
    return FileResponse(WEB_PRODUCT / "index.html")

@app.get("/login")
async def login_page():
    return FileResponse(WEB_PRODUCT / "login.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse(WEB_PRODUCT / "manifest.json", media_type="application/manifest+json")

@app.get("/sw.js")
async def service_worker():
    return FileResponse(WEB_PRODUCT / "sw.js", media_type="application/javascript")


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return {"ollama": True, "models": models}
    except Exception:
        return {"ollama": False, "models": []}


@app.get("/api/tools")
async def api_tools():
    """Catálogo completo de herramientas: categoría, riesgo y descripción."""
    try:
        from app.tools import TOOLS_SCHEMA, TOOL_CATEGORIES, DANGEROUS_TOOLS
        cat_of = {}
        for cat, names in TOOL_CATEGORIES.items():
            for n in names:
                cat_of.setdefault(n, cat)
        out = []
        for t in TOOLS_SCHEMA:
            fn = t.get("function", {})
            name = fn.get("name", "")
            desc = (fn.get("description", "") or "").split("\n")[0][:160]
            params = list((fn.get("parameters", {}).get("properties", {}) or {}).keys())
            out.append({
                "name": name,
                "category": cat_of.get(name, "otros"),
                "dangerous": name in DANGEROUS_TOOLS,
                "description": desc,
                "params": params,
            })
        out.sort(key=lambda x: (x["category"], x["name"]))
        return {"ok": True, "tools": out, "count": len(out)}
    except Exception as e:
        return {"ok": False, "error": str(e), "tools": []}


# ── A1.5: Carpetas / workspace (auth-gated) ───────────────────────────────────
def _gate(request: Request):
    return None if _auth_ok(request) else JSONResponse(
        {"ok": False, "error": "no autorizado"}, status_code=401)


@app.get("/api/folders")
async def api_folders(request: Request):
    g = _gate(request)
    if g:
        return g
    from app import database as db
    return {"ok": True, "folders": db.get_folders(), "conversations": db.get_conversations()}


@app.post("/api/folders")
async def api_folders_create(request: Request):
    g = _gate(request)
    if g:
        return g
    b = await request.json()
    name = (b.get("name") or "").strip()
    if not name:
        return JSONResponse({"ok": False, "error": "nombre requerido"}, status_code=400)
    from app import database as db
    fid = db.create_folder(name, b.get("parent_id"), b.get("color"),
                           b.get("context", ""), b.get("default_model"))
    return {"ok": True, "id": fid}


@app.patch("/api/folders/{folder_id}")
async def api_folders_update(folder_id: int, request: Request):
    g = _gate(request)
    if g:
        return g
    b = await request.json()
    from app import database as db
    db.update_folder(folder_id, **{k: b[k] for k in
                     ("name", "parent_id", "color", "context", "default_model", "position")
                     if k in b})
    return {"ok": True}


@app.delete("/api/folders/{folder_id}")
async def api_folders_delete(folder_id: int, request: Request):
    g = _gate(request)
    if g:
        return g
    from app import database as db
    db.delete_folder(folder_id)
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/move")
async def api_conv_move(conv_id: int, request: Request):
    g = _gate(request)
    if g:
        return g
    b = await request.json()
    from app import database as db
    db.move_conversation(conv_id, b.get("folder_id"))
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/color")
async def api_conv_color(conv_id: int, request: Request):
    g = _gate(request)
    if g:
        return g
    b = await request.json()
    from app import database as db
    db.set_conversation_color(conv_id, b.get("color"))
    return {"ok": True}


@app.get("/api/files")
async def api_files():
    """Archivos generados por el agente (documentos/imágenes) con su URL pública."""
    import time as _t
    try:
        from app.api.tunnel import get_public_url
        base = get_public_url()
    except Exception:
        base = ""
    items = []
    try:
        for p in sorted(_SERVED.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
            if not p.is_file():
                continue
            ext = p.suffix.lower().lstrip(".")
            kind = ("image" if ext in ("png", "jpg", "jpeg", "webp", "gif")
                    else "pdf" if ext == "pdf"
                    else "doc" if ext in ("html", "md", "txt", "docx") else "file")
            url = f"{base}/served/{p.name}" if base else f"/served/{p.name}"
            items.append({
                "name": p.name, "url": url, "kind": kind, "ext": ext,
                "bytes": p.stat().st_size, "mtime": int(p.stat().st_mtime),
            })
    except Exception as e:
        return {"ok": False, "error": str(e), "files": []}
    return {"ok": True, "files": items, "count": len(items),
            "public_base": base, "generated_at": int(_t.time())}


# ── Vision helper ─────────────────────────────────────────────────────────────

async def _describe_image(b64: str) -> str:
    # Fuente única de visión (local llava/qwen-vl → Pixtral nube). Ver app/vision.py.
    from app.vision import describe_image
    return await describe_image(b64)


# ── Watch mode (WATCH-001) ────────────────────────────────────────────────────

async def _watch_loop(ws: WebSocket, interval: int, duration: int, monitor: int,
                      stop_event: asyncio.Event):
    """Captures screenshots every `interval` seconds and streams them to the client."""
    from app.tools import execute_tool
    seq   = 0
    start = asyncio.get_event_loop().time()
    try:
        while not stop_event.is_set():
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed >= duration:
                break
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: execute_tool("screenshot_pc", {"monitor": monitor})
            )
            if "screenshot_base64" in result:
                await ws.send_json({
                    "type": "screenshot",
                    "data": {
                        "b64":     result["screenshot_base64"],
                        "fmt":     result.get("format", "jpeg"),
                        "size":    result.get("size", ""),
                        "monitor": monitor,
                        "seq":     seq,
                        "elapsed": int(elapsed),
                        "duration": duration,
                    },
                })
                seq += 1
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    except Exception:
        pass
    finally:
        try:
            await ws.send_json({"type": "watch_ended", "data": {"frames": seq}})
        except Exception:
            pass


# ── Device context ────────────────────────────────────────────────────────────

def _detect_device(request: Request) -> dict:
    """Detect PC vs mobile from User-Agent."""
    ua = request.headers.get("user-agent", "").lower()
    is_mobile = any(k in ua for k in ["android", "iphone", "ipad", "mobile"])
    platform  = "desconocida"
    if "android" in ua:
        platform = "Android"
    elif "iphone" in ua or "ipad" in ua:
        platform = "iOS"
    elif "windows" in ua:
        platform = "Windows"
    elif "mac" in ua:
        platform = "macOS"
    elif "linux" in ua:
        platform = "Linux"
    return {
        "is_mobile": is_mobile,
        "platform":  platform,
        "device":    "móvil" if is_mobile else "PC",
    }


# ── GPU request queue (one inference at a time) ───────────────────────────────
# Prevents model thrashing when PC + relay + iOS all send requests simultaneously.
# Clients receive a queue-position status while waiting; they can cancel without dropping.

_gpu_sem   = asyncio.Semaphore(1)
_gpu_waiters: list[asyncio.Event] = []   # ordered list so we can count position


async def _acquire_gpu(ws: WebSocket, priority: bool = False) -> bool:
    """Acquire the GPU semaphore. Returns False if the ws disconnects while waiting."""
    if _gpu_sem._value > 0:  # fast path: GPU free
        await _gpu_sem.acquire()
        return True

    # Announce queue position before blocking
    pos = len(_gpu_waiters) + 1
    wait_ev = asyncio.Event()
    if priority:
        _gpu_waiters.insert(0, wait_ev)
    else:
        _gpu_waiters.append(wait_ev)
    try:
        await ws.send_json({
            "type": "status",
            "data": f"GPU ocupada — posición {pos} en cola. Espera a que termine la tarea anterior…",
        })
        await _gpu_sem.acquire()
        return True
    except Exception:
        return False
    finally:
        if wait_ev in _gpu_waiters:
            _gpu_waiters.remove(wait_ev)


def _release_gpu():
    _gpu_sem.release()


# ── WebSocket Chat ────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_chat(ws: WebSocket):
    # Auth check via cookie in WS handshake (must accept before close per Starlette)
    token = ws.cookies.get("ca_token")
    await ws.accept()
    if not token or not verify_token(token):
        await ws.close(code=4401)
        return

    loop      = asyncio.get_running_loop()
    agent_q: asyncio.Queue = asyncio.Queue()
    runner    = None
    conv      : list[dict] = []
    _watch_stop: asyncio.Event | None = None
    _watch_task: asyncio.Task | None  = None

    # Detect device from WS headers
    ua         = ws.headers.get("user-agent", "").lower()
    is_mobile  = any(k in ua for k in ["android", "iphone", "ipad", "mobile"])
    platform   = "Android" if "android" in ua else ("iOS" if "iphone" in ua or "ipad" in ua else "PC")
    device_ctx = f"móvil {platform}" if is_mobile else "PC (escritorio)"

    status = await api_status()
    await ws.send_json({
        "type": "connected",
        "data": {**status, "device": platform, "is_mobile": is_mobile}
    })

    try:
        async def _start_watch(interval: int, duration: int, monitor: int):
            nonlocal _watch_stop, _watch_task
            if _watch_task and not _watch_task.done():
                _watch_stop.set()
                await asyncio.sleep(0)
            _watch_stop = asyncio.Event()
            _watch_task = asyncio.create_task(
                _watch_loop(ws, interval, duration, monitor, _watch_stop)
            )

        async def _stop_watch():
            nonlocal _watch_stop, _watch_task
            if _watch_stop:
                _watch_stop.set()

        async for data in ws.iter_json():
            t = data.get("type")

            # Watch mode: client-initiated
            if t == "watch_start":
                await _start_watch(
                    int(data.get("interval_sec", 5)),
                    int(data.get("duration_sec", 60)),
                    int(data.get("monitor", 0)),
                )
                await ws.send_json({"type": "status", "data": "Modo vigilancia iniciado."})
                continue

            if t == "watch_stop":
                await _stop_watch()
                continue

            if t and t.startswith("workspace:"):
                # Paridad local: carpetas/archivos/google por el mismo dispatch que el relay.
                ws_action = t.split(":", 1)[1]
                if ws_action == "google_connect":
                    from app import google_suite as _g
                    ws_data = await asyncio.to_thread(_g.google_connect)
                else:
                    from app import workspace as _wsmod
                    ws_data = _wsmod.handle_sync(ws_action, data)
                await ws.send_json({"type": "workspace:result", "req_id": data.get("req_id"),
                                    "action": ws_action, **ws_data})
                continue

            if t == "generate_image":
                # WEBPROD-005: paridad con el relay para el botón 🎨 en localhost.
                prompt = (data.get("content") or data.get("prompt") or "").strip()
                if not prompt:
                    continue
                await ws.send_json({"type": "status", "data": "🎨 Generando imagen…"})
                try:
                    from app.mistral_studio import available as _ms_av, run as _ms_run
                    if not _ms_av():
                        await ws.send_json({"type": "token",
                            "data": "No puedo crear imágenes: falta MISTRAL_API_KEY."})
                    else:
                        res = await asyncio.to_thread(_ms_run, prompt, ["image_generation"])
                        imgs = res.get("files") or []
                        if imgs:
                            import os as _os
                            try:
                                from app import database as _db
                                for f in imgs:
                                    _db.register_file(f.get("path", ""),
                                        name=_os.path.basename(f.get("path", "")) or "imagen.png",
                                        url=f.get("url"), conversation_id=data.get("conversation_id"),
                                        folder_id=data.get("folder_id"), kind="image")
                            except Exception:
                                pass
                            md = f"🎨 Imagen generada para: *{prompt}*\n\n" + "\n".join(
                                f"![imagen]({f.get('url')})" for f in imgs if f.get("url"))
                            await ws.send_json({"type": "token", "data": md})
                            await ws.send_json({"type": "files", "data": [
                                {"name": _os.path.basename(f.get("path", "")) or "imagen.png",
                                 "url": f.get("url"), "kind": "image"} for f in imgs]})
                        else:
                            await ws.send_json({"type": "token",
                                "data": (res or {}).get("text") or "No se generó ninguna imagen."})
                except Exception as e:
                    await ws.send_json({"type": "token", "data": f"Error generando la imagen: {e}"})
                await ws.send_json({"type": "done"})
                continue

            if t == "message":
                content = data.get("content", "").strip()
                images  = data.get("images", [])

                # Override device from client-reported info (more accurate)
                client_device = data.get("device")
                if client_device:
                    device_ctx = client_device

                if images:
                    await agent_q.put({"type": "status", "data": f"Analizando {len(images)} imagen(es)…"})
                    descs = []
                    for b64 in images[:3]:
                        if "," in b64:
                            b64 = b64.split(",", 1)[1]
                        descs.append(await _describe_image(b64))
                    if descs:
                        content += "\n\n[Imágenes compartidas]\n" + "\n\n---\n\n".join(descs)

                # WEBPROD-014/011: adjuntos NO-imagen (scripts/docs/pdf/csv…).
                files = data.get("files") or []
                if files:
                    try:
                        from app.attachments import process_attachments
                        content += process_attachments(files)
                    except Exception as e:
                        content += f"\n\n[archivo adjunto — error: {e}]"

                if not content:
                    continue

                # No dupliques el turno si el último mensaje ya era idéntico.
                _last = conv[-1] if conv else None
                if not (_last and _last.get("role") == "user" and _last.get("content") == content):
                    conv.append({"role": "user", "content": content})

                # Cap conversation history to avoid exceeding num_ctx silently
                conv_trimmed = conv[-40:]

                if runner:
                    runner.stop()

                # Fresh queue per message — prevents old runner events leaking into new response
                agent_q = asyncio.Queue()

                from app.api.agent_runner import AgentRunner

                # Expert mode: bypass approval for dangerous tools — local only (DEBATE-002).
                # Relay/remote sessions can never elevate to expert mode.
                client_host = ws.client.host if ws.client else ""
                is_local = client_host in ("127.0.0.1", "::1", "localhost")
                expert_mode = is_local and bool(data.get("expert_mode", False))
                if expert_mode:
                    try:
                        from app.agent_log import log as _alog
                        _alog("WARN", "server", "Sesión experta activada (auto-approve peligrosas)",
                              {"host": client_host, "device": device_ctx})
                    except Exception:
                        pass

                # GPU queue: one inference at a time. iOS/mobile gets priority (shorter tasks).
                is_mobile_client = any(k in device_ctx.lower() for k in ("iphone", "ios", "android", "móvil", "movil"))
                gpu_acquired = await _acquire_gpu(ws, priority=is_mobile_client)
                if not gpu_acquired:
                    continue  # WS disconnected while waiting

                try:
                    runner = AgentRunner(
                        messages         = list(conv_trimmed),
                        session_trust    = expert_mode or data.get("session_trust", False),
                        tool_permissions = data.get("permissions", {}),
                        device_context   = device_ctx,
                        expert_mode      = expert_mode,
                    )
                except Exception as _runner_exc:
                    _release_gpu()
                    await ws.send_json({"type": "error", "data": f"Error iniciando agente: {_runner_exc}"})
                    continue

                full: list[str] = []

                def _run():
                    try:
                        for evt in runner.events():
                            loop.call_soon_threadsafe(agent_q.put_nowait, evt)
                            if evt["type"] == "done":
                                full.append(evt.get("data", ""))
                    finally:
                        loop.call_soon_threadsafe(_release_gpu)

                threading.Thread(target=_run, daemon=True).start()

                _done_data: list[str] = []
                q_task = asyncio.create_task(agent_q.get())
                ws_task = asyncio.create_task(ws.receive_json())
                try:
                    while True:
                        done, _pending = await asyncio.wait(
                            {q_task, ws_task},
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        if q_task in done:
                            evt = q_task.result()
                            # Watch events: start/stop the loop without forwarding raw config
                            if evt["type"] == "watch_config":
                                cfg = evt.get("data", {})
                                await _start_watch(
                                    cfg.get("interval_sec", 5),
                                    cfg.get("duration_sec", 60),
                                    cfg.get("monitor", 0),
                                )
                                await ws.send_json({"type": "status", "data": cfg.get("message", "Vigilancia activada.")})
                                q_task = asyncio.create_task(agent_q.get())
                                continue
                            if evt["type"] == "watch_stop":
                                await _stop_watch()
                                q_task = asyncio.create_task(agent_q.get())
                                continue
                            await ws.send_json(evt)
                            if evt["type"] in ("done", "error"):
                                if evt["type"] == "done" and evt.get("data"):
                                    _done_data.append(evt["data"])
                                elif full:
                                    _done_data.append(full[0])
                                if _done_data:
                                    conv.append({"role": "assistant", "content": _done_data[0]})
                                break
                            q_task = asyncio.create_task(agent_q.get())

                        if ws_task in done:
                            incoming = ws_task.result()
                            incoming_t = incoming.get("type")
                            if incoming_t == "approve" and runner:
                                runner.approve(
                                    incoming.get("tool_id", ""),
                                    bool(incoming.get("approved", False)),
                                )
                            elif incoming_t == "stop" and runner:
                                runner.stop()
                            elif incoming_t == "message":
                                await ws.send_json({
                                    "type": "status",
                                    "data": "Ya hay una tarea en curso; espera a que termine o aprueba/rechaza la herramienta pendiente.",
                                })
                            ws_task = asyncio.create_task(ws.receive_json())
                finally:
                    for task in (q_task, ws_task):
                        if task and not task.done():
                            task.cancel()

            elif t == "approve" and runner:
                runner.approve(data["tool_id"], bool(data.get("approved", False)))

            elif t == "stop" and runner:
                runner.stop()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
    finally:
        if runner:
            runner.stop()
        if _watch_stop:
            _watch_stop.set()
        if _watch_task and not _watch_task.done():
            _watch_task.cancel()


# ── Terminal WebSocket ────────────────────────────────────────────────────────

_MAX_TERMINAL_SESSIONS = 3
_terminal_count = 0
_MAX_CMD_BYTES = 4096

@app.websocket("/terminal")
async def terminal_ws(ws: WebSocket):
    global _terminal_count
    token = ws.cookies.get("ca_token")
    await ws.accept()
    if not token or not verify_token(token):
        await ws.close(code=4401)
        return
    if _terminal_count >= _MAX_TERMINAL_SESSIONS:
        await ws.close(code=4429, reason="Too many terminal sessions")
        return

    _terminal_count += 1
    proc = await asyncio.create_subprocess_exec(
        "powershell", "-NoLogo", "-NoProfile", "-Command", "-",
        stdin =asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def _read():
        while True:
            chunk = await proc.stdout.read(2048)
            if not chunk:
                break
            try:
                await ws.send_text(chunk.decode("utf-8", errors="replace"))
            except Exception:
                break

    reader = asyncio.create_task(_read())
    try:
        while True:
            cmd = await asyncio.wait_for(ws.receive_text(), timeout=300.0)
            if proc.returncode is not None:
                break
            if proc.stdin:
                proc.stdin.write((cmd[:_MAX_CMD_BYTES] + "\n").encode())
                await proc.stdin.drain()
    except Exception:
        pass
    finally:
        _terminal_count -= 1
        reader.cancel()
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass


# ── Start ─────────────────────────────────────────────────────────────────────

def start_server(port: int = 8765):
    import uvicorn
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    srv = uvicorn.Server(cfg)

    def _run():
        try:
            srv.run()
        except Exception as e:
            # Bajo pythonw el stderr se pierde: registramos el fallo real del server.
            try:
                from app.agent_log import log_exception
                log_exception("api_server", f"uvicorn murió en :{port}: {e}")
            except Exception:
                pass

    t = threading.Thread(target=_run, daemon=True, name="cyberagent-api")
    t.start()
    return srv
