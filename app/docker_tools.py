"""
Gestión de Docker para el agente de CyberAgent.

"Docker = posibilidades infinitas": el agente puede listar, levantar, parar,
reiniciar, ver logs/recursos, inspeccionar, ejecutar comandos y manejar
docker-compose. Incluye el contenedor de Home Assistant / comunicaciones que ya
existe en el Docker local. Acción sensible (controla servicios reales) →
DANGEROUS_TOOLS: requiere aprobación.

Todo vía el CLI `docker`/`docker compose` en subproceso, con timeouts y salida
acotada para no inundar el contexto del modelo.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

_MAX_OUT = 6000   # chars de salida devueltos al modelo


def _docker_bin() -> str | None:
    return shutil.which("docker")


def available() -> bool:
    return bool(_docker_bin())


def _run_cli(args: list[str], timeout: int = 60, cwd: str | None = None) -> dict:
    docker = _docker_bin()
    if not docker:
        return {"ok": False, "error": "docker no está instalado o no está en PATH"}
    try:
        r = subprocess.run(
            [docker] + args, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out = (r.stdout or "") + (("\n" + r.stderr) if r.returncode != 0 and r.stderr else "")
        return {"ok": r.returncode == 0, "exit": r.returncode, "output": out[:_MAX_OUT]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _ps(all_: bool = False) -> dict:
    args = ["ps", "--format", "{{json .}}"]
    if all_:
        args.append("-a")
    r = _run_cli(args, timeout=20)
    if not r.get("ok"):
        return r
    rows = []
    for line in (r["output"] or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            rows.append({"name": d.get("Names"), "image": d.get("Image"),
                         "status": d.get("Status"), "state": d.get("State"),
                         "ports": d.get("Ports", "")})
        except Exception:
            pass
    return {"ok": True, "count": len(rows), "containers": rows}


def run(op: str, name: str = "", params: dict | None = None) -> dict:
    """Dispatcher de operaciones Docker.

    op:
      ps / ps_all          → lista contenedores (activos / todos)
      images               → lista imágenes
      start/stop/restart   → controla un contenedor (name)
      logs                 → últimas líneas de log (params.tail, def 100)
      stats                → uso de CPU/MEM de un contenedor (snapshot)
      inspect              → detalle JSON de un contenedor
      rm                   → elimina un contenedor (params.force)
      pull                 → descarga una imagen (name = imagen)
      run                  → docker run (params.image, params.args[], params.detach)
      exec                 → ejecuta un comando dentro (params.cmd)
      compose_up/down/ps   → docker compose en params.path (carpeta del compose)
    """
    op = (op or "").lower().strip()
    p = params or {}

    if op in ("ps", "list"):
        return _ps(False)
    if op in ("ps_all", "ps-all"):
        return _ps(True)
    if op == "images":
        return _run_cli(["images", "--format", "{{.Repository}}:{{.Tag}}  {{.Size}}"], timeout=20)
    if op in ("start", "stop", "restart"):
        if not name:
            return {"ok": False, "error": "falta 'name' del contenedor"}
        return _run_cli([op, name], timeout=60)
    if op == "logs":
        if not name:
            return {"ok": False, "error": "falta 'name'"}
        tail = str(int(p.get("tail", 100)))
        return _run_cli(["logs", "--tail", tail, name], timeout=30)
    if op == "stats":
        if not name:
            return {"ok": False, "error": "falta 'name'"}
        return _run_cli(["stats", "--no-stream", "--format",
                         "{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}} ({{.MemPerc}})", name], timeout=20)
    if op == "inspect":
        if not name:
            return {"ok": False, "error": "falta 'name'"}
        return _run_cli(["inspect", name], timeout=20)
    if op == "rm":
        if not name:
            return {"ok": False, "error": "falta 'name'"}
        args = ["rm"]
        if p.get("force"):
            args.append("-f")
        return _run_cli(args + [name], timeout=30)
    if op == "pull":
        image = name or p.get("image", "")
        if not image:
            return {"ok": False, "error": "falta la imagen"}
        return _run_cli(["pull", image], timeout=600)
    if op == "run":
        image = p.get("image", "") or name
        if not image:
            return {"ok": False, "error": "falta params.image"}
        args = ["run"]
        if p.get("detach", True):
            args.append("-d")
        if p.get("name"):
            args += ["--name", str(p["name"])]
        for port in (p.get("ports") or []):
            args += ["-p", str(port)]
        for env in (p.get("env") or []):
            args += ["-e", str(env)]
        args.append(image)
        if isinstance(p.get("args"), list):
            args += [str(a) for a in p["args"]]
        return _run_cli(args, timeout=120)
    if op == "exec":
        if not name or not p.get("cmd"):
            return {"ok": False, "error": "falta 'name' y/o params.cmd"}
        cmd = p["cmd"]
        cmd_list = cmd if isinstance(cmd, list) else ["sh", "-c", str(cmd)]
        return _run_cli(["exec", name] + cmd_list, timeout=120)
    if op in ("compose_up", "compose-up"):
        path = p.get("path", "")
        if not path or not os.path.isdir(path):
            return {"ok": False, "error": "params.path debe ser la carpeta del docker-compose"}
        return _run_cli(["compose", "up", "-d"], timeout=300, cwd=path)
    if op in ("compose_down", "compose-down"):
        path = p.get("path", "")
        if not path or not os.path.isdir(path):
            return {"ok": False, "error": "params.path inválido"}
        return _run_cli(["compose", "down"], timeout=120, cwd=path)
    if op in ("compose_ps", "compose-ps"):
        path = p.get("path", "")
        if not path or not os.path.isdir(path):
            return {"ok": False, "error": "params.path inválido"}
        return _run_cli(["compose", "ps"], timeout=30, cwd=path)

    # J-02: actualizar límites de recursos de un contenedor en caliente
    if op in ("update", "resources"):
        if not name:
            return {"ok": False, "error": "falta 'name' del contenedor"}
        args = ["update"]
        if p.get("cpus"):
            args += ["--cpus", str(p["cpus"])]
        if p.get("memory"):
            args += ["--memory", str(p["memory"])]
        if p.get("memory_swap"):
            args += ["--memory-swap", str(p["memory_swap"])]
        if p.get("cpu_shares"):
            args += ["--cpu-shares", str(p["cpu_shares"])]
        if len(args) == 1:
            return {"ok": False, "error": "falta al menos un parámetro de recurso: cpus, memory, memory_swap, cpu_shares"}
        return _run_cli(args + [name], timeout=30)

    return {"ok": False, "error": f"operación Docker desconocida: {op}"}
