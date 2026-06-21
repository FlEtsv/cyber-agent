"""
CyberAgent — Cloud Run: notificaciones, persistencia GCS, proxy al PC via túnel.
"""
import base64, json, logging, os, time
import httpx
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pywebpush import webpush, WebPushException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cyberagent")

# ── Config ─────────────────────────────────────────────────────────────────
SECRET       = os.environ.get("SECRET", "change-me-in-cloud-run")
VAPID_PUBLIC = os.environ.get("VAPID_PUBLIC", "")
VAPID_EMAIL  = os.environ.get("VAPID_EMAIL", "stevenflet13@gmail.com")
VAPID_CLAIMS = {"sub": f"mailto:{VAPID_EMAIL}"}
GCS_BUCKET   = os.environ.get("GCS_BUCKET", "")

_vapid_b64    = os.environ.get("VAPID_PRIVATE_B64", "")
VAPID_PRIVATE = base64.b64decode(_vapid_b64).decode() if _vapid_b64 else ""

app = FastAPI(title="CyberAgent")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Estado en memoria ──────────────────────────────────────────────────────
_subscription: dict | None = None
_pending: dict[str, dict]  = {}   # token → {status, decision, ts, data}
_tunnel_url: str | None    = None  # URL del túnel Cloudflare registrado por el PC

# ── GCS helpers ────────────────────────────────────────────────────────────
_GCS_BLOB = "push_subscription.json"

def _gcs_load() -> dict | None:
    if not GCS_BUCKET:
        return None
    try:
        from google.cloud import storage
        client = storage.Client()
        blob   = client.bucket(GCS_BUCKET).blob(_GCS_BLOB)
        if blob.exists():
            return json.loads(blob.download_as_text())
    except Exception as e:
        log.warning(f"[GCS] load: {e}")
    return None

def _gcs_save(sub: dict):
    if not GCS_BUCKET:
        return
    try:
        from google.cloud import storage
        client = storage.Client()
        blob   = client.bucket(GCS_BUCKET).blob(_GCS_BLOB)
        blob.upload_from_string(json.dumps(sub), content_type="application/json")
        log.info("[GCS] suscripción guardada")
    except Exception as e:
        log.warning(f"[GCS] save: {e}")

# Cargar suscripción al arrancar (Cloud Run puede escalar a 0)
_subscription = _gcs_load()
if _subscription:
    log.info("[GCS] suscripción restaurada al arrancar")

# ── Auth ────────────────────────────────────────────────────────────────────
def _auth(secret: str | None):
    if secret != SECRET:
        raise HTTPException(403, "Forbidden")

# ── Push helper ─────────────────────────────────────────────────────────────
def _push(payload: dict):
    if not _subscription or not VAPID_PRIVATE:
        log.warning("[push] Sin suscripción o VAPID no configurado")
        return
    try:
        webpush(
            subscription_info=_subscription,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=VAPID_PRIVATE,
            vapid_claims=VAPID_CLAIMS,
        )
        log.info(f"[push] Enviado: {payload.get('title')}")
    except WebPushException as e:
        log.error(f"[push] Error: {e}")

# ── Proxy helper ─────────────────────────────────────────────────────────────
def _pc_headers():
    return {"X-Secret": SECRET}

# ════════════════════════════════════════════════════════════════════════════
# PÁGINAS
# ════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "subscribe.html",
        {"request": request, "vapid_public": VAPID_PUBLIC},
    )

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/terminal", response_class=HTMLResponse)
async def terminal_page(request: Request):
    return templates.TemplateResponse("terminal.html", {"request": request})

# ════════════════════════════════════════════════════════════════════════════
# SUSCRIPCIÓN PUSH
# ════════════════════════════════════════════════════════════════════════════

@app.post("/subscribe")
async def subscribe(request: Request):
    global _subscription
    _subscription = await request.json()
    _gcs_save(_subscription)
    log.info("[subscribe] Suscripción registrada y persistida en GCS")
    return {"ok": True}

@app.get("/vapid-public")
async def vapid_public():
    return {"key": VAPID_PUBLIC}

# ════════════════════════════════════════════════════════════════════════════
# TÚNEL — PC registra su URL de Cloudflare
# ════════════════════════════════════════════════════════════════════════════

@app.post("/register-tunnel")
async def register_tunnel(
    request: Request,
    x_secret: str | None = Header(None, alias="X-Secret"),
):
    global _tunnel_url
    _auth(x_secret)
    data        = await request.json()
    _tunnel_url = data.get("url", "").rstrip("/")
    log.info(f"[tunnel] PC registrado: {_tunnel_url}")
    return {"ok": True}

@app.get("/tunnel-url")
async def get_tunnel_url(x_secret: str | None = Header(None, alias="X-Secret")):
    _auth(x_secret)
    return {"url": _tunnel_url}

# ════════════════════════════════════════════════════════════════════════════
# NOTIFICACIONES (PC → Cloud Run → móvil)
# ════════════════════════════════════════════════════════════════════════════

@app.post("/notify")
async def notify(
    request: Request,
    x_secret: str | None = Header(None, alias="X-Secret"),
):
    _auth(x_secret)
    _push(await request.json())
    return {"ok": True}

# ════════════════════════════════════════════════════════════════════════════
# APROBACIONES
# ════════════════════════════════════════════════════════════════════════════

@app.post("/approval/request")
async def approval_request(
    request: Request,
    x_secret: str | None = Header(None, alias="X-Secret"),
):
    _auth(x_secret)
    data  = await request.json()
    token = data["tool_id"]
    _pending[token] = {"status": "pending", "decision": None,
                       "ts": time.time(), "data": data}
    args_preview = json.dumps(data.get("args", {}), ensure_ascii=False)[:80]
    _push({
        "type": "approval", "title": f"⚡ Herramienta: {data['tool_name']}",
        "body": args_preview, "token": token, "requireInteraction": True,
    })
    return {"ok": True, "token": token}

@app.post("/approval/{token}/decide")
async def decide(token: str, request: Request):
    body = await request.json()
    if token not in _pending:
        raise HTTPException(404, "Token no encontrado")
    _pending[token]["status"]   = "decided"
    _pending[token]["decision"] = body.get("decision", "reject")
    log.info(f"[approval] {token} → {_pending[token]['decision']}")
    return {"ok": True}

@app.get("/approval/{token}/poll")
async def poll(token: str, x_secret: str | None = Header(None, alias="X-Secret")):
    _auth(x_secret)
    entry = _pending.get(token)
    if not entry:
        return {"status": "not_found"}
    if time.time() - entry["ts"] > 600:
        _pending.pop(token, None)
        return {"status": "expired"}
    return {"status": entry["status"], "decision": entry["decision"]}

# ════════════════════════════════════════════════════════════════════════════
# PROXY API → PC (requiere túnel registrado)
# ════════════════════════════════════════════════════════════════════════════

def _require_tunnel():
    if not _tunnel_url:
        raise HTTPException(503, "PC no disponible — túnel no registrado")
    return _tunnel_url

@app.get("/api/status")
async def api_status():
    tunnel = _require_tunnel()
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{tunnel}/status", headers=_pc_headers())
        return r.json()

@app.post("/api/chat/start")
async def api_chat_start(request: Request):
    tunnel = _require_tunnel()
    body   = await request.json()
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{tunnel}/chat/start",
                              json=body, headers=_pc_headers())
        return r.json()

@app.get("/api/chat/{session_id}/stream")
async def api_chat_stream(session_id: str):
    tunnel = _require_tunnel()

    async def _proxy():
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "GET",
                f"{tunnel}/chat/{session_id}/stream",
                headers={**_pc_headers(), "Accept": "text/event-stream"},
            ) as resp:
                async for line in resp.aiter_lines():
                    yield line + "\n"

    return StreamingResponse(
        _proxy(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/api/chat/{session_id}/approve/{tool_id}")
async def api_approve(session_id: str, tool_id: str, request: Request):
    tunnel = _require_tunnel()
    body   = await request.json()
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(
            f"{tunnel}/chat/{session_id}/approve/{tool_id}",
            json=body, headers=_pc_headers(),
        )
        return r.json()

@app.post("/api/terminal/token")
async def api_terminal_token():
    """Obtiene un token de un solo uso + URL WS directo al túnel."""
    tunnel = _require_tunnel()
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(f"{tunnel}/terminal/token", headers=_pc_headers())
        data = r.json()
        ws_tunnel = tunnel.replace("https://", "wss://").replace("http://", "ws://")
        return {**data, "ws_url": ws_tunnel}

# ════════════════════════════════════════════════════════════════════════════
# HEALTHCHECK
# ════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "ok":         True,
        "subscribed": _subscription is not None,
        "pending":    len(_pending),
        "tunnel":     _tunnel_url is not None,
        "gcs":        bool(GCS_BUCKET),
    }
