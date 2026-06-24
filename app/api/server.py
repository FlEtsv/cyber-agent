"""CyberAgent Web Server — FastAPI + WebSocket + PWA + Auth."""
import asyncio, json, os, threading
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import httpx

from app.auth import (
    is_setup_done, setup_user, verify_login,
    create_token, verify_token, get_totp_qr_svg,
)

WEB_DIR = Path(__file__).parent.parent / "web"

app = FastAPI(docs_url=None, redoc_url=None)
_ALLOWED_ORIGINS = [o for o in [
    "http://localhost:8765",
    "http://127.0.0.1:8765",
    os.environ.get("CYBERAGENT_CLOUD_URL", ""),
] if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


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
    return FileResponse(WEB_DIR / "index.html")

@app.get("/login")
async def login_page():
    return FileResponse(WEB_DIR / "login.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse(WEB_DIR / "manifest.json", media_type="application/manifest+json")

@app.get("/sw.js")
async def service_worker():
    return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript")


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


# ── Vision helper ─────────────────────────────────────────────────────────────

async def _describe_image(b64: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("http://localhost:11434/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]
        vision = next(
            (m for m in models if any(k in m.lower()
             for k in ["llava", "vision", "moondream", "bakllava", "qwen2-vl", "qwen2.5-vl"])),
            None,
        )
        if not vision:
            return "[imagen adjunta — instala un modelo de visión como llava para analizarla]"
        async with httpx.AsyncClient(timeout=45) as c:
            r = await c.post("http://localhost:11434/api/generate", json={
                "model": vision,
                "prompt": (
                    "Describe detalladamente lo que ves en esta imagen. "
                    "Incluye: texto visible, elementos de interfaz, objetos, colores, "
                    "contexto y cualquier información relevante. Responde en español."
                ),
                "images": [b64],
                "stream": False,
            })
        return r.json().get("response", "[error al describir imagen]")
    except Exception as e:
        return f"[imagen adjunta — error: {e}]"


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
        async for data in ws.iter_json():
            t = data.get("type")

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

                if not content:
                    continue

                conv.append({"role": "user", "content": content})

                # Cap conversation history to avoid exceeding num_ctx silently
                conv_trimmed = conv[-40:]

                if runner:
                    runner.stop()

                # Fresh queue per message — prevents old runner events leaking into new response
                agent_q = asyncio.Queue()

                from app.api.agent_runner import AgentRunner
                runner = AgentRunner(
                    messages         = list(conv_trimmed),
                    session_trust    = data.get("session_trust", False),
                    tool_permissions = data.get("permissions", {}),
                    device_context   = device_ctx,
                )

                full: list[str] = []

                def _run():
                    for evt in runner.events():
                        loop.call_soon_threadsafe(agent_q.put_nowait, evt)
                        if evt["type"] == "done":
                            full.append(evt.get("data", ""))

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
    t   = threading.Thread(target=srv.run, daemon=True, name="cyberagent-api")
    t.start()
    return srv
