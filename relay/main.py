"""
CyberAgent Cloud Relay — runs on Cloud Run.
Acts as a fixed-URL bridge between the mobile browser and the PC agent.

PC connects outbound  → wss://<relay>/host?secret=HOST_SECRET
Mobile browser        → wss://<relay>/ws  (after login)
"""
import asyncio, collections, json, os, secrets, time, uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import bcrypt
import pyotp
import qrcode, qrcode.image.svg, io
from jose import jwt, JWTError

# ── Config (all from env vars) ────────────────────────────────────────────────
HOST_SECRET   = os.environ.get("HOST_SECRET", "change-me")
RELAY_EMAIL   = os.environ.get("RELAY_EMAIL", "")
RELAY_PW_HASH = os.environ.get("RELAY_PW_HASH", "")    # bcrypt hash
RELAY_TOTP    = os.environ.get("RELAY_TOTP_SECRET", "")
JWT_SECRET    = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET env var is required — set it in Cloud Run secrets")

# TOTP is mandatory by default on the relay.
# Set TOTP_OPTIONAL=1 only in dev/test environments without an authenticator app.
TOTP_REQUIRED = os.environ.get("TOTP_OPTIONAL", "0").lower() not in ("1", "true", "yes")

if TOTP_REQUIRED and not RELAY_TOTP:
    import sys
    print(
        "WARNING: TOTP_REQUIRED is active but RELAY_TOTP_SECRET is not set. "
        "All logins will be rejected until RELAY_TOTP_SECRET is configured. "
        "Set TOTP_OPTIONAL=1 to disable 2FA (not recommended for production).",
        file=sys.stderr,
    )
JWT_ALGO      = "HS256"
JWT_HOURS     = 72

WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(docs_url=None, redoc_url=None)


# ── Rate limiting (in-memory, per IP) ─────────────────────────────────────────
_RATE_WINDOW = 300   # seconds
_RATE_MAX    = 10    # max login attempts per window per IP
_rate_hits: dict[str, collections.deque] = {}

def _rate_ok(ip: str) -> bool:
    now = time.time()
    dq = _rate_hits.setdefault(ip, collections.deque())
    while dq and dq[0] < now - _RATE_WINDOW:
        dq.popleft()
    if len(dq) >= _RATE_MAX:
        return False
    dq.append(now)
    return True

STATIC_DIR = WEB_DIR / "static"
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR if STATIC_DIR.exists() else WEB_DIR)),
    name="static",
)


# ── State: one PC host connection, N mobile sessions ─────────────────────────
class RelayState:
    def __init__(self):
        self.host_ws: WebSocket | None = None
        self.host_q:  asyncio.Queue    = asyncio.Queue(maxsize=100)
        self.sessions: dict[str, WebSocket] = {}   # session_id → mobile ws
        self._send_fn = None  # set/cleared only inside host_ws coroutine

    def pc_online(self) -> bool:
        return self._send_fn is not None

state = RelayState()


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _verify_login(email: str, pw: str, totp: str) -> bool:
    if email != RELAY_EMAIL:
        return False
    if not RELAY_PW_HASH:
        return False
    if not bcrypt.checkpw(pw.encode(), RELAY_PW_HASH.encode()):
        return False
    if TOTP_REQUIRED:
        if not RELAY_TOTP:
            return False  # secret not configured → block until admin sets it up
        return pyotp.TOTP(RELAY_TOTP).verify(totp, valid_window=1)
    if RELAY_TOTP:
        return pyotp.TOTP(RELAY_TOTP).verify(totp, valid_window=1)
    return True

def _make_token(email: str) -> str:
    return jwt.encode(
        {"sub": email, "exp": int(time.time()) + JWT_HOURS * 3600},
        JWT_SECRET, algorithm=JWT_ALGO,
    )

def _check_token(request: Request) -> bool:
    token = request.cookies.get("ca_token")
    if not token:
        return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return True
    except JWTError:
        return False

def _check_ws_token(ws: WebSocket) -> bool:
    token = ws.cookies.get("ca_token")
    if not token:
        return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return True
    except JWTError:
        return False


# ── Auth API ──────────────────────────────────────────────────────────────────
@app.get("/api/auth/status")
async def auth_status():
    return {
        "setup_done": bool(RELAY_EMAIL and RELAY_PW_HASH),
        "totp_required": TOTP_REQUIRED or bool(RELAY_TOTP),
    }

@app.post("/api/auth/login")
async def auth_login(req: Request):
    ip = req.client.host if req.client else "unknown"
    if not _rate_ok(ip):
        return JSONResponse({"ok": False, "error": "Demasiados intentos. Espera unos minutos."}, status_code=429)
    body  = await req.json()
    email = body.get("email", "").strip()
    pw    = body.get("password", "")
    totp  = body.get("totp", "").strip().replace(" ", "")
    if not _verify_login(email, pw, totp):
        return JSONResponse({"ok": False, "error": "Credenciales incorrectas"}, status_code=401)
    token = _make_token(email)
    resp  = JSONResponse({"ok": True})
    resp.set_cookie("ca_token", token, httponly=True, samesite="lax",
                    secure=True, max_age=JWT_HOURS * 3600)
    return resp

@app.post("/api/auth/logout")
async def auth_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("ca_token")
    return resp

@app.post("/api/auth/setup")
async def auth_setup_dummy():
    return JSONResponse({"ok": False, "error": "Configura credenciales via env vars"}, 400)


# ── Pages ─────────────────────────────────────────────────────────────────────
@app.get("/")
async def index(request: Request):
    if not _check_token(request):
        return RedirectResponse("/login")
    return FileResponse(WEB_DIR / "index.html")

@app.get("/login")
async def login_page():
    return FileResponse(WEB_DIR / "login.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse(WEB_DIR / "manifest.json", media_type="application/manifest+json")

@app.get("/sw.js")
async def sw():
    return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript")

@app.get("/api/status")
async def api_status():
    return {"relay": True, "pc_online": state.pc_online()}


# ── PC host WebSocket (/host) ─────────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def _generic_exc(request: Request, exc: Exception):
    return JSONResponse({"error": "Error interno del servidor"}, status_code=500)


@app.websocket("/host")
async def host_ws(ws: WebSocket, secret: str = ""):
    await ws.accept()
    if secret != HOST_SECRET:
        await ws.close(code=4401)
        return

    # Reject a second PC while one is already connected
    if state.host_ws is not None:
        await ws.close(code=4409, reason="Host already connected")
        return

    state.host_ws = ws

    async def _send_to_pc(msg: dict):
        try:
            await ws.send_json(msg)
        except Exception:
            try:
                state.host_q.put_nowait(msg)
            except asyncio.QueueFull:
                pass  # queue full — discard silently

    state._send_fn = _send_to_pc

    # Drain any queued messages (sessions that opened before PC reconnected)
    while not state.host_q.empty():
        try:
            await ws.send_json(state.host_q.get_nowait())
        except Exception:
            break

    try:
        async for raw in ws.iter_text():
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            session_id = msg.get("session_id")
            if not session_id:
                continue
            mobile = state.sessions.get(session_id)
            if mobile:
                payload = {k: v for k, v in msg.items() if k != "session_id"}
                try:
                    await mobile.send_json(payload)
                except Exception:
                    state.sessions.pop(session_id, None)
    except WebSocketDisconnect:
        pass
    finally:
        state.host_ws = None
        state._send_fn = None
        # Notify all mobile sessions
        for sid, mob in list(state.sessions.items()):
            try:
                await mob.send_json({"type": "error",
                                     "data": "PC desconectado. Reconectando…"})
            except Exception:
                pass


# ── Mobile chat WebSocket (/ws) ───────────────────────────────────────────────
@app.websocket("/ws")
async def mobile_ws(ws: WebSocket):
    await ws.accept()
    if not _check_ws_token(ws):
        await ws.close(code=4401)
        return
    session_id = str(uuid.uuid4())
    state.sessions[session_id] = ws

    # Tell mobile relay status
    await ws.send_json({
        "type": "connected",
        "data": {"relay": True, "pc_online": state.pc_online(),
                 "models": [], "session_id": session_id},
    })

    if not state.pc_online():
        await ws.send_json({"type": "error",
                            "data": "El PC no está conectado al relay. "
                                    "Asegúrate de que CyberAgent está corriendo en tu PC."})

    try:
        async for raw in ws.iter_text():
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            send_fn = state._send_fn
            if send_fn:
                await send_fn({**msg, "session_id": session_id})
            else:
                await ws.send_json({"type": "error",
                                    "data": "PC no conectado"})
    except WebSocketDisconnect:
        pass
    finally:
        state.sessions.pop(session_id, None)
        send_fn = state._send_fn
        if send_fn:
            try:
                await send_fn({"type": "session_closed",
                               "session_id": session_id})
            except Exception:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
