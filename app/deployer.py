"""
Despliega apps/scripts creados por el agente y los expone por una URL pública.

Dos modos (el agente elige según el proyecto):
  • ESTÁTICO  (carpeta con index.html, o un .html suelto): se copia a
    app/web/served/apps/<slug>/ y se sirve por el server local → sale por el
    túnel Cloudflare PRINCIPAL ya existente: {tunnel}/served/apps/<slug>/
  • DINÁMICO  (Python/Node con servidor propio): instala dependencias, arranca
    el proceso en un puerto libre y le pone un túnel Cloudflare DEDICADO →
    URL pública propia (https://<algo>.trycloudflare.com).

Pensado para "lo que el agente decida": detecta el tipo, instala lo que haga
falta, abre el puerto y lo tuneliza. Cada despliegue se puede parar.
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import time

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APPS_DIR = os.path.join(_BASE, "app", "web", "served", "apps")
# Registro PERSISTENTE de lo que el agente despliega (sobrevive reinicios) → así
# el usuario tiene "en un sitio ordenado" las herramientas/apps creadas para él.
_REGISTRY = os.path.join(_BASE, "data", "deployments.json")


def _load_registry() -> list:
    try:
        import json
        with open(_REGISTRY, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _register(slug: str, name: str, kind: str, url: str) -> None:
    import json
    import time as _t
    items = [x for x in _load_registry() if x.get("slug") != slug]
    items.insert(0, {"slug": slug, "name": name or slug, "kind": kind,
                     "url": url, "created": _t.time()})
    try:
        os.makedirs(os.path.dirname(_REGISTRY), exist_ok=True)
        with open(_REGISTRY, "w", encoding="utf-8") as f:
            json.dump(items[:50], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def registered_deployments() -> dict:
    """Apps/herramientas desplegadas (persistente). Para la vista de la web."""
    return {"count": len(_load_registry()), "deployments": _load_registry()}

# slug -> dict(kind, url, port, proc, tunnel_proc, dir, name, started)
_DEPLOYMENTS: dict[str, dict] = {}
_LOCK = threading.Lock()

_TRYCF = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


# ── utilidades ────────────────────────────────────────────────────────────────
def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", (name or "app").strip().lower()).strip("-")
    return s or "app"


def _unique_slug(name: str) -> str:
    base = _slugify(name)
    slug = base
    i = 2
    while slug in _DEPLOYMENTS:
        slug = f"{base}-{i}"
        i += 1
    return slug


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _find_cloudflared() -> str | None:
    try:
        from app.api.tunnel import TunnelManager
        return TunnelManager._find_cloudflared()
    except Exception:
        import shutil
        return shutil.which("cloudflared")


def detect_kind(path: str) -> str:
    """'static' | 'python' | 'node' a partir de la ruta del proyecto."""
    if os.path.isfile(path):
        return "static" if path.lower().endswith((".html", ".htm")) else "python" if path.lower().endswith(".py") else "node" if path.lower().endswith((".js", ".mjs")) else "static"
    files = set(os.listdir(path)) if os.path.isdir(path) else set()
    if "package.json" in files or any(f.endswith((".js", ".mjs", ".ts")) for f in files):
        if "package.json" in files:
            return "node"
    if any(f.endswith(".py") for f in files) or "requirements.txt" in files:
        return "python"
    if "index.html" in files or any(f.endswith((".html", ".htm")) for f in files):
        return "static"
    if "package.json" in files:
        return "node"
    return "static"


# ── túnel dedicado (sin tocar el singleton global de tunnel.py) ────────────────
def _spawn_app_tunnel(port: int, wait_secs: float = 40.0) -> tuple[str | None, subprocess.Popen | None]:
    cf = _find_cloudflared()
    if not cf:
        return None, None
    proc = subprocess.Popen(
        [cf, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    url_box: dict[str, str] = {}

    def _reader():
        try:
            for line in proc.stdout:
                m = _TRYCF.search(line)
                if m and "url" not in url_box:
                    url_box["url"] = m.group(0)
        except Exception:
            pass

    threading.Thread(target=_reader, daemon=True, name=f"cf-app-{port}").start()
    deadline = time.time() + wait_secs
    while time.time() < deadline and "url" not in url_box:
        if proc.poll() is not None:
            break
        time.sleep(0.25)
    return url_box.get("url"), proc


# ── despliegue ────────────────────────────────────────────────────────────────
def _publish_static(slug: str, path: str) -> dict:
    import shutil
    dst = os.path.join(_APPS_DIR, slug)
    if os.path.isdir(dst):
        shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    if os.path.isfile(path):
        shutil.copy2(path, os.path.join(dst, "index.html"
                     if path.lower().endswith((".html", ".htm")) else os.path.basename(path)))
    else:
        shutil.copytree(path, dst, dirs_exist_ok=True)

    try:
        from app.api.tunnel import ensure_tunnel, get_public_url
        public = get_public_url() or ensure_tunnel(wait_secs=20)
    except Exception:
        public = ""
    rel = f"/served/apps/{slug}/"
    url = (public.rstrip("/") + rel) if public else rel
    return {"ok": True, "kind": "static", "slug": slug, "url": url,
            "local_url": f"http://localhost:8765{rel}"}


def _entrypoint(path: str, kind: str) -> str | None:
    if os.path.isfile(path):
        return path
    names = (["server.js", "index.js", "app.js", "main.js"] if kind == "node"
             else ["app.py", "main.py", "server.py", "run.py", "wsgi.py"])
    for n in names:
        if os.path.isfile(os.path.join(path, n)):
            return os.path.join(path, n)
    return None


def _install_deps(workdir: str, kind: str, log: list):
    try:
        if kind == "python" and os.path.isfile(os.path.join(workdir, "requirements.txt")):
            log.append("pip install -r requirements.txt …")
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
                           cwd=workdir, timeout=300,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        elif kind == "node" and os.path.isfile(os.path.join(workdir, "package.json")):
            npm = "npm.cmd" if os.name == "nt" else "npm"
            log.append("npm install …")
            subprocess.run([npm, "install", "--no-fund", "--no-audit"],
                           cwd=workdir, timeout=400,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        log.append(f"deps: {e}")


def _publish_dynamic(slug: str, path: str, kind: str, run_cmd: str | None) -> dict:
    workdir = path if os.path.isdir(path) else os.path.dirname(path)
    port = _free_port()
    log: list[str] = []
    _install_deps(workdir, kind, log)

    env = dict(os.environ)
    env["PORT"] = str(port)          # convención que leen Flask/Express/etc.
    env["HOST"] = "0.0.0.0"

    if run_cmd:
        cmd = run_cmd if isinstance(run_cmd, list) else run_cmd.split()
    else:
        entry = _entrypoint(path, kind)
        if not entry:
            return {"ok": False, "error": "no encuentro el archivo de arranque; pasa run_cmd"}
        if kind == "python":
            cmd = [sys.executable, entry]
        else:
            npm = "npm.cmd" if os.name == "nt" else "npm"
            cmd = ([npm, "start"] if os.path.isfile(os.path.join(workdir, "package.json"))
                   and not entry.endswith((".js", ".mjs")) else ["node", entry])

    try:
        proc = subprocess.Popen(cmd, cwd=workdir, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return {"ok": False, "error": f"no se pudo arrancar: {e}", "cmd": cmd}

    time.sleep(2.5)                  # margen para que el server levante
    if proc.poll() is not None:
        out = ""
        try:
            out = proc.stdout.read()[:600]
        except Exception:
            pass
        return {"ok": False, "error": "el proceso terminó al arrancar", "output": out, "cmd": cmd}

    url, tproc = _spawn_app_tunnel(port)
    if not url:
        try:
            proc.terminate()
        except Exception:
            pass
        return {"ok": False, "error": "no se pudo crear el túnel (¿cloudflared instalado?)",
                "hint": "winget install Cloudflare.cloudflared"}

    with _LOCK:
        _DEPLOYMENTS[slug] = {"kind": kind, "url": url, "port": port, "proc": proc,
                              "tunnel_proc": tproc, "dir": workdir, "name": slug,
                              "started": time.time()}
    _register(slug, slug, kind, url)
    return {"ok": True, "kind": kind, "slug": slug, "url": url, "port": port, "log": log}


def publish(path: str, name: str | None = None, kind: str | None = None,
            run_cmd: str | None = None) -> dict:
    """Despliega lo que hay en `path` y devuelve la URL pública.

    path    : carpeta del proyecto o archivo suelto (.html/.py/.js).
    name    : nombre legible (define el slug de la URL para estáticos).
    kind    : 'static'|'python'|'node' (autodetecta si se omite).
    run_cmd : comando de arranque para apps dinámicas (opcional).
    """
    if not path or not os.path.exists(path):
        return {"ok": False, "error": f"ruta no encontrada: {path}"}
    kind = kind or detect_kind(path)
    slug = _unique_slug(name or os.path.basename(path.rstrip("/\\")) or kind)
    os.makedirs(_APPS_DIR, exist_ok=True)
    if kind == "static":
        res = _publish_static(slug, path)
        with _LOCK:
            _DEPLOYMENTS[slug] = {"kind": "static", "url": res.get("url"), "port": None,
                                  "proc": None, "tunnel_proc": None,
                                  "dir": path, "name": name or slug, "started": time.time()}
        _register(slug, name or slug, "static", res.get("url"))
        return res
    return _publish_dynamic(slug, path, kind, run_cmd)


def list_deployments() -> dict:
    with _LOCK:
        items = [{"slug": s, "kind": d["kind"], "url": d["url"],
                  "port": d.get("port"),
                  "alive": (d["proc"] is None or d["proc"].poll() is None)}
                 for s, d in _DEPLOYMENTS.items()]
    return {"count": len(items), "deployments": items}


def stop(slug: str) -> dict:
    with _LOCK:
        d = _DEPLOYMENTS.pop(slug, None)
    if not d:
        return {"ok": False, "error": f"no hay despliegue '{slug}'"}
    for key in ("proc", "tunnel_proc"):
        p = d.get(key)
        if p:
            try:
                p.terminate()
            except Exception:
                pass
    if d["kind"] == "static":
        import shutil
        shutil.rmtree(os.path.join(_APPS_DIR, slug), ignore_errors=True)
    return {"ok": True, "stopped": slug}


def stop_all():
    for slug in list(_DEPLOYMENTS.keys()):
        stop(slug)
