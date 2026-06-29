"""
Generación de documentos y publicación por URL.

- generate_document: crea PDF / HTML / Markdown / TXT a partir de contenido.
- serve_file: copia un archivo a la carpeta pública y devuelve una URL accesible
  por el usuario a través del túnel Cloudflare ya existente.

Los archivos se guardan en app/web/served, que el servidor local expone en /served.
"""
from __future__ import annotations

import os
import re
import shutil
import time

_BASE = os.path.dirname(__file__)
SERVED_DIR = os.path.join(_BASE, "web", "served")


def _ensure() -> str:
    os.makedirs(SERVED_DIR, exist_ok=True)
    return SERVED_DIR


def _safe_name(name: str, default_ext: str) -> str:
    name = os.path.basename(name or "").strip() or f"doc_{int(time.time())}"
    name = re.sub(r"[^A-Za-z0-9._\-]", "_", name)
    if "." not in name:
        name += default_ext
    return name


def public_url_for(path: str) -> str:
    """URL pública para un archivo ya situado en SERVED_DIR (o lo copia allí)."""
    _ensure()
    fname = os.path.basename(path)
    target = os.path.join(SERVED_DIR, fname)
    if os.path.abspath(path) != os.path.abspath(target):
        try:
            shutil.copy2(path, target)
        except Exception:
            pass
    base = ""
    try:
        from app.api.tunnel import ensure_tunnel, get_public_url
        base = get_public_url()
        if not base:
            # Arranca el túnel y espera el enlace público (hasta 15s) para que
            # "correr script → URL" funcione sin que el usuario tenga que pensarlo.
            base = ensure_tunnel(wait_secs=15.0)
    except Exception:
        base = ""
    if base:
        return f"{base}/served/{fname}"
    # Fallback: ruta local accesible en LAN
    return f"http://localhost:8765/served/{fname}"


def _md_to_html(md_text: str, title: str) -> str:
    try:
        import markdown
        body = markdown.markdown(md_text, extensions=["fenced_code", "tables"])
    except Exception:
        body = "<pre>" + (md_text or "").replace("<", "&lt;") + "</pre>"
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
 body{{font:16px/1.6 system-ui,Segoe UI,sans-serif;max-width:820px;margin:40px auto;
       padding:0 20px;color:#1a1a1a;background:#fff}}
 pre{{background:#0d1117;color:#e6edf3;padding:14px;border-radius:8px;overflow:auto}}
 code{{font-family:Consolas,monospace}} table{{border-collapse:collapse}}
 td,th{{border:1px solid #ccc;padding:6px 10px}} h1,h2,h3{{line-height:1.25}}
</style></head><body>{body}</body></html>"""


def generate_document(content: str, filename: str = "documento", fmt: str = "pdf",
                      title: str | None = None) -> dict:
    """
    Genera un documento y lo deja listo para servir.
    fmt: pdf | html | md | txt
    """
    fmt = (fmt or "pdf").strip().lower()
    title = title or os.path.splitext(os.path.basename(filename or "Documento"))[0]
    _ensure()

    try:
        if fmt == "pdf":
            fname = _safe_name(filename, ".pdf")
            path = os.path.join(SERVED_DIR, fname)
            _write_pdf(content, path, title)
        elif fmt == "html":
            fname = _safe_name(filename, ".html")
            path = os.path.join(SERVED_DIR, fname)
            with open(path, "w", encoding="utf-8") as f:
                f.write(_md_to_html(content, title))
        elif fmt in ("md", "markdown"):
            fname = _safe_name(filename, ".md")
            path = os.path.join(SERVED_DIR, fname)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        else:  # txt
            fname = _safe_name(filename, ".txt")
            path = os.path.join(SERVED_DIR, fname)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "fmt": fmt}

    return {
        "ok": True,
        "fmt": fmt,
        "path": path,
        "filename": fname,
        "url": public_url_for(path),
        "bytes": os.path.getsize(path),
    }


def _write_pdf(content: str, path: str, title: str) -> None:
    """PDF con reportlab; respeta saltos de línea y párrafos básicos de Markdown."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10.5, leading=15)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, leading=22)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, leading=18)
    code = ParagraphStyle("code", parent=styles["Code"], fontSize=9, leading=12,
                          backColor="#f2f2f2")

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title=title)
    flow = [Paragraph(_esc(title), h1), Spacer(1, 10)]
    in_code = False
    code_buf: list[str] = []
    for raw in (content or "").splitlines():
        if raw.strip().startswith("```"):
            if in_code:
                flow.append(Preformatted("\n".join(code_buf), code))
                code_buf = []
            in_code = not in_code
            continue
        if in_code:
            code_buf.append(raw)
            continue
        line = raw.rstrip()
        if not line:
            flow.append(Spacer(1, 6))
        elif line.startswith("## "):
            flow.append(Paragraph(_esc(line[3:]), h2))
        elif line.startswith("# "):
            flow.append(Paragraph(_esc(line[2:]), h1))
        else:
            flow.append(Paragraph(_esc(line), body))
    if code_buf:
        flow.append(Preformatted("\n".join(code_buf), code))
    doc.build(flow)


def _esc(s: str) -> str:
    s = (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # negritas markdown simples
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', s)
    return s


def serve_file(path: str) -> dict:
    """Publica un archivo existente y devuelve su URL."""
    if not os.path.isfile(path):
        return {"ok": False, "error": f"No existe el archivo: {path}"}
    try:
        url = public_url_for(path)
        return {"ok": True, "url": url, "filename": os.path.basename(path),
                "bytes": os.path.getsize(path)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
