"""Servidor FastAPI local — expone capacidades del PC vía Cloudflare Tunnel."""
import asyncio, json, os, time, uuid, threading
from fastapi import FastAPI, WebSocket, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

SECRET = os.environ.get("CYBERAGENT_CLOUD_SECRET", "")

app = FastAPI(title="CyberAgent Local API", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, object]  = {}   # session_id → AgentRunner
_term_tokens: dict[str, float] = {}  # one-time WS auth tokens


def _check_secret(x_secret: str | None = Header(None, alias="X-Secret")):
    if SECRET and x_secret != SECRET:
        raise HTTPException(401, "No autorizado")


# ── Estado ──────────────────────────────────────────────────────────────────
@app.get("/status")
async def status(_=Depends(_check_secret)):
    import httpx
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        ollama = True
    except Exception:
        models = []
        ollama = False
    return {"ok": True, "ollama": ollama, "models": models,
            "sessions": len(_sessions)}


# ── Chat SSE ────────────────────────────────────────────────────────────────
@app.post("/chat/start")
async def chat_start(req: dict, _=Depends(_check_secret)):
    from app.api.agent_runner import AgentRunner
    sid    = str(uuid.uuid4())
    runner = AgentRunner(
        messages         = req.get("messages", []),
        session_trust    = req.get("session_trust", False),
        tool_permissions = req.get("permissions", {}),
    )
    _sessions[sid] = runner
    return {"session_id": sid}


@app.get("/chat/{session_id}/stream")
async def chat_stream(session_id: str, _=Depends(_check_secret)):
    runner = _sessions.get(session_id)
    if not runner:
        raise HTTPException(404, "Sesión no encontrada")

    def _gen():
        for evt in runner.events():
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        _sessions.pop(session_id, None)

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/{session_id}/approve/{tool_id}")
async def approve_tool(session_id: str, tool_id: str, req: dict,
                       _=Depends(_check_secret)):
    runner = _sessions.get(session_id)
    if not runner:
        raise HTTPException(404)
    runner.approve(tool_id, bool(req.get("approved", False)))
    return {"ok": True}


# ── Terminal one-time tokens ─────────────────────────────────────────────────
@app.post("/terminal/token")
async def terminal_token(_=Depends(_check_secret)):
    tok = str(uuid.uuid4())
    _term_tokens[tok] = time.time()
    # Limpiar tokens expirados (>90 s)
    cutoff  = time.time() - 90
    expired = [k for k, ts in list(_term_tokens.items()) if ts < cutoff]
    for k in expired:
        _term_tokens.pop(k, None)
    return {"token": tok}


# ── Terminal WebSocket ────────────────────────────────────────────────────────
@app.websocket("/terminal")
async def terminal_ws(ws: WebSocket, token: str | None = None):
    ts = _term_tokens.pop(token, None) if token else None
    if ts is None or time.time() - ts > 90:
        await ws.close(code=4001)
        return

    await ws.accept()
    proc = await asyncio.create_subprocess_exec(
        "powershell", "-NoLogo", "-NoProfile", "-Command", "-",
        stdin =asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def _read():
        while True:
            data = await proc.stdout.read(2048)
            if not data:
                break
            try:
                await ws.send_text(data.decode("utf-8", errors="replace"))
            except Exception:
                break

    reader = asyncio.create_task(_read())
    try:
        while True:
            cmd = await ws.receive_text()
            if proc.stdin:
                proc.stdin.write((cmd + "\n").encode())
                await proc.stdin.drain()
    except Exception:
        pass
    finally:
        reader.cancel()
        try:
            proc.terminate()
        except Exception:
            pass


# ── Arrancar en hilo daemon ───────────────────────────────────────────────────
def start_server(port: int = 8765):
    import uvicorn
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    srv = uvicorn.Server(cfg)
    t   = threading.Thread(target=srv.run, daemon=True, name="cyberagent-api")
    t.start()
    return srv
