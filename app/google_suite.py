"""
Integración con Google Workspace (Gmail, Drive, Calendar) — leer y ayudar.

OAuth de usuario (una sola vez): necesitas un "OAuth client" de Google Cloud Console
guardado en  data/google_credentials.json . La primera llamada abre el navegador para
autorizar y guarda el token en  data/google_token.json  (reutilizable, se auto-refresca).

Todo CPU/red (no usa GPU). Imports perezosos: si faltan las libs o las credenciales,
las tools devuelven un mensaje claro sin romper la app.

Setup (una vez):
  1. console.cloud.google.com → crea proyecto → habilita Gmail/Drive/Calendar API.
  2. Credenciales → OAuth client ID → tipo "App de escritorio" → descarga el JSON.
  3. Guárdalo como  data/google_credentials.json .
"""
from __future__ import annotations

import os
import base64

_DATA = os.path.join(os.path.dirname(__file__), "..", "data")
_CREDS = os.path.join(_DATA, "google_credentials.json")
_TOKEN = os.path.join(_DATA, "google_token.json")

# Lectura + envío de correo, lectura de Drive y Calendar.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

_SETUP_MSG = ("Falta data/google_credentials.json (OAuth client de Google Cloud Console, "
              "tipo 'App de escritorio'). Habilita Gmail/Drive/Calendar API, descarga el "
              "JSON y guárdalo ahí. Luego la primera llamada abrirá el navegador para autorizar.")


def _get_creds():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except Exception:
        return None, {"ok": False, "error": "instala: pip install google-api-python-client "
                      "google-auth-httplib2 google-auth-oauthlib"}
    creds = None
    if os.path.exists(_TOKEN):
        try:
            creds = Credentials.from_authorized_user_file(_TOKEN, SCOPES)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds or not creds.valid:
            if not os.path.exists(_CREDS):
                return None, {"ok": False, "error": _SETUP_MSG}
            try:
                flow = InstalledAppFlow.from_client_secrets_file(_CREDS, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                return None, {"ok": False, "error": f"autorización fallida: {e}"}
        try:
            os.makedirs(_DATA, exist_ok=True)
            with open(_TOKEN, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception:
            pass
    return creds, None


def _service(api: str, version: str):
    creds, err = _get_creds()
    if err:
        return None, err
    try:
        from googleapiclient.discovery import build
        return build(api, version, credentials=creds, cache_discovery=False), None
    except Exception as e:
        return None, {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _headers(payload) -> dict:
    return {h["name"].lower(): h["value"] for h in payload.get("headers", [])}


def _extract_body(payload) -> str:
    """Saca el texto plano de un mensaje Gmail (recorre partes)."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        txt = _extract_body(part)
        if txt:
            return txt
    # fallback: cualquier body con data
    data = payload.get("body", {}).get("data")
    return base64.urlsafe_b64decode(data).decode("utf-8", "replace") if data else ""


# ── Gmail ────────────────────────────────────────────────────────────────────
def gmail_search(query: str = "", max_results: int = 10) -> dict:
    """Busca correos (sintaxis Gmail: 'from:x is:unread newer_than:7d ...')."""
    svc, err = _service("gmail", "v1")
    if err:
        return err
    try:
        res = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        out = []
        for m in res.get("messages", []):
            msg = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]).execute()
            h = _headers(msg.get("payload", {}))
            out.append({"id": m["id"], "from": h.get("from"), "subject": h.get("subject"),
                        "date": h.get("date"), "snippet": msg.get("snippet", "")[:160]})
        return {"ok": True, "count": len(out), "messages": out}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def gmail_read(message_id: str) -> dict:
    """Lee el cuerpo completo de un correo por su id (de gmail_search)."""
    svc, err = _service("gmail", "v1")
    if err:
        return err
    try:
        msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
        h = _headers(msg.get("payload", {}))
        body = _extract_body(msg.get("payload", {}))
        return {"ok": True, "from": h.get("from"), "to": h.get("to"),
                "subject": h.get("subject"), "date": h.get("date"), "body": body[:8000]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def gmail_send(to: str, subject: str, body: str) -> dict:
    """Envía un correo desde tu cuenta (acción sensible: pide aprobación)."""
    svc, err = _service("gmail", "v1")
    if err:
        return err
    try:
        from email.mime.text import MIMEText
        mime = MIMEText(body, _charset="utf-8")
        mime["to"] = to
        mime["subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"ok": True, "id": sent.get("id"), "to": to, "subject": subject}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ── Drive ────────────────────────────────────────────────────────────────────
def gdrive_search(query: str = "", max_results: int = 10) -> dict:
    """Busca archivos en Drive. query: texto libre o sintaxis Drive ('name contains x')."""
    svc, err = _service("drive", "v3")
    if err:
        return err
    try:
        q = query if any(op in query for op in ("contains", "=", "mimeType")) else (
            f"fullText contains '{query}'" if query else None)
        res = svc.files().list(q=q, pageSize=max_results,
                               fields="files(id,name,mimeType,modifiedTime,size,webViewLink)").execute()
        return {"ok": True, "count": len(res.get("files", [])), "files": res.get("files", [])}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def gdrive_read(file_id: str) -> dict:
    """Lee el contenido de un archivo de Drive (exporta Google Docs/Sheets a texto)."""
    svc, err = _service("drive", "v3")
    if err:
        return err
    try:
        meta = svc.files().get(fileId=file_id, fields="name,mimeType").execute()
        mime = meta.get("mimeType", "")
        if mime.startswith("application/vnd.google-apps"):
            export = {"document": "text/plain", "spreadsheet": "text/csv",
                      "presentation": "text/plain"}.get(mime.split(".")[-1], "text/plain")
            data = svc.files().export(fileId=file_id, mimeType=export).execute()
        else:
            data = svc.files().get_media(fileId=file_id).execute()
        text = data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else str(data)
        return {"ok": True, "name": meta.get("name"), "mime": mime, "content": text[:10000]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ── Calendar ─────────────────────────────────────────────────────────────────
def gcalendar_events(max_results: int = 10, days: int = 7) -> dict:
    """Lista los próximos eventos del calendario principal (siguientes `days` días)."""
    svc, err = _service("calendar", "v3")
    if err:
        return err
    try:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        res = svc.events().list(
            calendarId="primary", timeMin=now.isoformat(),
            timeMax=(now + timedelta(days=days)).isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=max_results).execute()
        out = []
        for e in res.get("items", []):
            out.append({"summary": e.get("summary"),
                        "start": (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date"),
                        "end": (e.get("end") or {}).get("dateTime") or (e.get("end") or {}).get("date"),
                        "location": e.get("location")})
        return {"ok": True, "count": len(out), "events": out}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
