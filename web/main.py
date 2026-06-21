"""
CyberAgent — Cloud Run notification service.
Recibe eventos del PC y los reenvía como Web Push al móvil/browser.
"""
import json, os, time, logging
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pywebpush import webpush, WebPushException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cyberagent")

# ── Config (env vars en Cloud Run) ────────────────────────────────────────
import base64

SECRET        = os.environ.get("SECRET", "change-me-in-cloud-run")
VAPID_PUBLIC  = os.environ.get("VAPID_PUBLIC", "")
VAPID_EMAIL   = os.environ.get("VAPID_EMAIL", "stevenflet13@gmail.com")
VAPID_CLAIMS  = {"sub": f"mailto:{VAPID_EMAIL}"}

# Clave privada guardada en base64 para evitar problemas con newlines en env vars
_vapid_b64    = os.environ.get("VAPID_PRIVATE_B64", "")
VAPID_PRIVATE = base64.b64decode(_vapid_b64).decode() if _vapid_b64 else ""

app = FastAPI(title="CyberAgent Notifications")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Estado en memoria ─────────────────────────────────────────────────────
# Single-user: una sola suscripción push.
# Se restaura automáticamente cuando el browser visita la página.
_subscription: dict | None = None
_pending: dict[str, dict] = {}   # token → {status, decision, ts, data}


# ── Helpers ───────────────────────────────────────────────────────────────
def _auth(secret: str | None):
    if secret != SECRET:
        raise HTTPException(403, "Forbidden")

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


# ── Página de suscripción (se abre una vez desde el móvil) ───────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "subscribe.html",
        {"request": request, "vapid_public": VAPID_PUBLIC},
    )


# ── Browser → Cloud Run: registrar suscripción push ──────────────────────
@app.post("/subscribe")
async def subscribe(request: Request):
    global _subscription
    _subscription = await request.json()
    log.info("[subscribe] Suscripción registrada")
    return {"ok": True}


@app.get("/vapid-public")
async def vapid_public():
    return {"key": VAPID_PUBLIC}


# ── PC → Cloud Run: enviar notificación genérica ─────────────────────────
@app.post("/notify")
async def notify(
    request: Request,
    x_secret: str | None = Header(None, alias="X-Secret"),
):
    _auth(x_secret)
    data = await request.json()
    _push(data)
    return {"ok": True}


# ── PC → Cloud Run: solicitar aprobación de herramienta ──────────────────
@app.post("/approval/request")
async def approval_request(
    request: Request,
    x_secret: str | None = Header(None, alias="X-Secret"),
):
    _auth(x_secret)
    data = await request.json()   # {tool_id, tool_name, args}
    token = data["tool_id"]

    _pending[token] = {
        "status":   "pending",
        "decision": None,
        "ts":       time.time(),
        "data":     data,
    }

    args_preview = json.dumps(data.get("args", {}), ensure_ascii=False)[:80]
    _push({
        "type":             "approval",
        "title":            f"⚡ Herramienta: {data['tool_name']}",
        "body":             args_preview,
        "token":            token,
        "requireInteraction": True,
    })
    return {"ok": True, "token": token}


# ── Browser → Cloud Run: usuario aprueba/rechaza desde notificación ───────
@app.post("/approval/{token}/decide")
async def decide(token: str, request: Request):
    body = await request.json()   # {decision: "approve" | "reject"}
    if token not in _pending:
        raise HTTPException(404, "Token no encontrado")
    _pending[token]["status"]   = "decided"
    _pending[token]["decision"] = body.get("decision", "reject")
    log.info(f"[approval] {token} → {_pending[token]['decision']}")
    return {"ok": True}


# ── PC → Cloud Run: polling resultado de aprobación ──────────────────────
@app.get("/approval/{token}/poll")
async def poll(
    token: str,
    x_secret: str | None = Header(None, alias="X-Secret"),
):
    _auth(x_secret)
    entry = _pending.get(token)
    if not entry:
        return {"status": "not_found"}
    # Limpia entradas viejas (>10 min)
    if time.time() - entry["ts"] > 600:
        _pending.pop(token, None)
        return {"status": "expired"}
    return {"status": entry["status"], "decision": entry["decision"]}


# ── Healthcheck ───────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "ok":         True,
        "subscribed": _subscription is not None,
        "pending":    len(_pending),
    }
