import subprocess, os, json, shutil, sys
from datetime import datetime

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "shell",
        "description": "Ejecuta un comando en PowerShell (Windows) o bash (WSL Ubuntu). "
                       "Usa shell_type='powershell' para comandos Windows y 'bash' para Linux.",
        "parameters": {"type": "object", "properties": {
            "command":    {"type": "string", "description": "Comando a ejecutar"},
            "shell_type": {"type": "string", "enum": ["powershell", "bash", "cmd"],
                           "description": "Shell: 'powershell' (default), 'bash' (WSL), 'cmd'"},
            "timeout":    {"type": "integer", "description": "Timeout en segundos (default 60)"},
        }, "required": ["command"]}
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Lee el contenido de un archivo del sistema.",
        "parameters": {"type": "object", "properties": {
            "path":   {"type": "string", "description": "Ruta del archivo"},
            "offset": {"type": "integer", "description": "Línea desde donde empezar (default 0)"},
            "limit":  {"type": "integer", "description": "Máximo de líneas a leer (default todas)"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Escribe o sobreescribe un archivo. Crea directorios intermedios si no existen.",
        "parameters": {"type": "object", "properties": {
            "path":    {"type": "string", "description": "Ruta del archivo"},
            "content": {"type": "string", "description": "Contenido a escribir"},
            "append":  {"type": "boolean", "description": "Si true, añade al final en vez de sobreescribir"},
        }, "required": ["path", "content"]}
    }},
    {"type": "function", "function": {
        "name": "list_directory",
        "description": "Lista el contenido de un directorio con tamaños y fechas.",
        "parameters": {"type": "object", "properties": {
            "path":      {"type": "string", "description": "Ruta del directorio"},
            "recursive": {"type": "boolean", "description": "Listar recursivamente"},
        }, "required": ["path"]}
    }},
    {"type": "function", "function": {
        "name": "web_fetch",
        "description": "Descarga el contenido de una URL y devuelve el texto extraído.",
        "parameters": {"type": "object", "properties": {
            "url":     {"type": "string", "description": "URL a descargar"},
            "headers": {"type": "object", "description": "Headers HTTP adicionales"},
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "run_python",
        "description": "Ejecuta código Python arbitrario y devuelve stdout/stderr. "
                       "Úsalo para análisis de datos, cálculos, o tareas que requieren lógica compleja.",
        "parameters": {"type": "object", "properties": {
            "code":    {"type": "string", "description": "Código Python a ejecutar"},
            "timeout": {"type": "integer", "description": "Timeout en segundos (default 30)"},
        }, "required": ["code"]}
    }},
    {"type": "function", "function": {
        "name": "list_processes",
        "description": "Lista procesos en ejecución con uso de CPU y memoria.",
        "parameters": {"type": "object", "properties": {
            "filter_name": {"type": "string", "description": "Filtrar por nombre de proceso (opcional)"},
            "sort_by":     {"type": "string", "enum": ["memory", "cpu", "name", "pid"],
                           "description": "Ordenar por (default: memory)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "install_package",
        "description": "Instala un paquete de software usando el gestor indicado: "
                       "pip (Python), winget (Windows apps), npm (Node.js), choco (Chocolatey), apt (WSL/Linux).",
        "parameters": {"type": "object", "properties": {
            "package": {"type": "string", "description": "Nombre del paquete a instalar"},
            "manager": {"type": "string", "enum": ["pip", "winget", "npm", "choco", "apt"],
                       "description": "Gestor de paquetes"},
            "version": {"type": "string", "description": "Versión específica (opcional)"},
        }, "required": ["package", "manager"]}
    }},
    {"type": "function", "function": {
        "name": "uninstall_package",
        "description": "Desinstala un paquete usando el gestor indicado.",
        "parameters": {"type": "object", "properties": {
            "package": {"type": "string", "description": "Nombre del paquete a desinstalar"},
            "manager": {"type": "string", "enum": ["pip", "winget", "npm", "choco", "apt"],
                       "description": "Gestor de paquetes"},
        }, "required": ["package", "manager"]}
    }},
    {"type": "function", "function": {
        "name": "system_info",
        "description": "Obtiene información completa del sistema: OS, hardware, red, procesos, espacio en disco.",
        "parameters": {"type": "object", "properties": {
            "section": {"type": "string",
                       "enum": ["all", "os", "hardware", "network", "processes", "disk"],
                       "description": "Sección de información (default: all)"},
        }, "required": []}
    }},
]

DANGEROUS_TOOLS = {"shell", "write_file", "run_python", "install_package", "uninstall_package"}


def is_dangerous(name: str) -> bool:
    return name in DANGEROUS_TOOLS


def execute_tool(name: str, args: dict) -> dict:
    try:
        dispatch = {
            "shell":             lambda: _shell(
                                     args.get("command", ""),
                                     args.get("shell_type", "powershell"),
                                     int(args.get("timeout", 60)),
                                 ),
            "read_file":         lambda: _read_file(
                                     args["path"],
                                     args.get("offset", 0),
                                     args.get("limit"),
                                 ),
            "write_file":        lambda: _write_file(
                                     args["path"],
                                     args["content"],
                                     bool(args.get("append", False)),
                                 ),
            "list_directory":    lambda: _list_dir(
                                     args["path"],
                                     bool(args.get("recursive", False)),
                                 ),
            "web_fetch":         lambda: _web_fetch(
                                     args["url"],
                                     args.get("headers", {}),
                                 ),
            "run_python":        lambda: _run_python(
                                     args["code"],
                                     int(args.get("timeout", 30)),
                                 ),
            "list_processes":    lambda: _list_processes(
                                     args.get("filter_name", ""),
                                     args.get("sort_by", "memory"),
                                 ),
            "install_package":   lambda: _install_package(
                                     args["package"],
                                     args["manager"],
                                     args.get("version", ""),
                                 ),
            "uninstall_package": lambda: _uninstall_package(
                                     args["package"],
                                     args["manager"],
                                 ),
            "system_info":       lambda: _system_info(
                                     args.get("section", "all"),
                                 ),
        }
        if name not in dispatch:
            return {"error": f"Herramienta desconocida: {name}"}
        return dispatch[name]()
    except KeyError as e:
        return {"error": f"Argumento requerido: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ── Implementaciones ───────────────────────────────────────────────────────

def _shell(command: str, shell_type: str = "powershell", timeout: int = 60) -> dict:
    if shell_type == "bash":
        cmd = ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-c", command]
    elif shell_type == "cmd":
        cmd = ["cmd.exe", "/c", command]
    else:
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        return {
            "stdout":     r.stdout[:10000],
            "stderr":     r.stderr[:3000],
            "returncode": r.returncode,
            "shell":      shell_type,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout ({timeout}s)"}


def _read_file(path: str, offset: int = 0, limit=None) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    if os.path.isdir(path):
        return {"error": f"Es un directorio: {path}"}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    total = len(lines)
    if offset:
        lines = lines[offset:]
    if limit:
        lines = lines[:limit]
    content = "".join(lines)
    return {
        "path":    path,
        "content": content[:20000],
        "size":    os.path.getsize(path),
        "lines":   total,
        "shown":   f"{offset}–{offset + len(lines)}",
    }


def _write_file(path: str, content: str, append: bool = False) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "path": path, "bytes": len(content.encode()), "mode": mode}


def _list_dir(path: str, recursive: bool = False) -> dict:
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.exists(path):
        return {"error": f"No encontrado: {path}"}
    entries = []
    if recursive:
        for root, dirs, files in os.walk(path):
            for d in dirs:
                full = os.path.join(root, d)
                entries.append({"name": os.path.relpath(full, path), "type": "dir", "size": None})
            for f in files:
                full = os.path.join(root, f)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    size = None
                entries.append({"name": os.path.relpath(full, path), "type": "file", "size": size})
            if len(entries) > 500:
                entries.append({"truncated": True})
                break
    else:
        for e in os.scandir(path):
            entries.append({
                "name":     e.name,
                "type":     "dir" if e.is_dir() else "file",
                "size":     e.stat().st_size if e.is_file() else None,
                "modified": datetime.fromtimestamp(e.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return {"path": path, "entries": sorted(entries, key=lambda x: (x.get("type", ""), x.get("name", "")))}


def _web_fetch(url: str, headers: dict | None = None) -> dict:
    import urllib.request, re
    default_headers = {"User-Agent": "Mozilla/5.0 (CyberAgent/1.0)"}
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)}
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return {"url": url, "content": text[:15000], "length": len(text)}


def _run_python(code: str, timeout: int = 30) -> dict:
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        return {
            "stdout":     r.stdout[:10000],
            "stderr":     r.stderr[:3000],
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout ({timeout}s)"}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _list_processes(filter_name: str = "", sort_by: str = "memory") -> dict:
    import psutil
    sort_keys = {
        "memory": lambda p: (p.get("mem_mb", 0), 0),
        "cpu":    lambda p: (p.get("cpu", 0), 0),
        "name":   lambda p: (p.get("name", ""), 0),
        "pid":    lambda p: (p.get("pid", 0), 0),
    }
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = p.info
            if filter_name and filter_name.lower() not in info["name"].lower():
                continue
            procs.append({
                "pid":    info["pid"],
                "name":   info["name"],
                "mem_mb": round(info["memory_info"].rss / 1024 ** 2, 1),
                "cpu":    info["cpu_percent"],
                "status": info["status"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    key = sort_keys.get(sort_by, sort_keys["memory"])
    procs.sort(key=key, reverse=sort_by in ("memory", "cpu"))
    return {"processes": procs[:60], "total": len(procs)}


def _install_package(package: str, manager: str, version: str = "") -> dict:
    pkg = f"{package}=={version}" if version and manager == "pip" else package
    if version and manager in ("choco", "winget"):
        pkg = f"{package} --version {version}"

    cmds = {
        "pip":    [sys.executable, "-m", "pip", "install", "--upgrade", pkg],
        "winget": ["winget", "install", "--id", package, "--accept-package-agreements",
                   "--accept-source-agreements", "-e"],
        "npm":    ["npm", "install", "-g", pkg],
        "choco":  ["choco", "install", package, "-y"],
        "apt":    ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-c",
                   f"sudo apt-get update && sudo apt-get install -y {package}"],
    }
    if manager not in cmds:
        return {"error": f"Gestor no soportado: {manager}"}

    try:
        r = subprocess.run(
            cmds[manager], capture_output=True, text=True,
            timeout=300, encoding="utf-8", errors="replace",
        )
        return {
            "manager":    manager,
            "package":    package,
            "stdout":     r.stdout[:6000],
            "stderr":     r.stderr[:2000],
            "returncode": r.returncode,
            "success":    r.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout (300s) — la instalación tardó demasiado"}
    except FileNotFoundError:
        return {"error": f"'{manager}' no está instalado o no está en el PATH"}


def _uninstall_package(package: str, manager: str) -> dict:
    cmds = {
        "pip":    [sys.executable, "-m", "pip", "uninstall", "-y", package],
        "winget": ["winget", "uninstall", "--id", package, "-e"],
        "npm":    ["npm", "uninstall", "-g", package],
        "choco":  ["choco", "uninstall", package, "-y"],
        "apt":    ["wsl", "-d", "Ubuntu-24.04", "--", "bash", "-c",
                   f"sudo apt-get remove -y {package}"],
    }
    if manager not in cmds:
        return {"error": f"Gestor no soportado: {manager}"}
    try:
        r = subprocess.run(
            cmds[manager], capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace",
        )
        return {
            "manager":    manager,
            "package":    package,
            "stdout":     r.stdout[:4000],
            "returncode": r.returncode,
            "success":    r.returncode == 0,
        }
    except FileNotFoundError:
        return {"error": f"'{manager}' no encontrado"}


def _system_info(section: str = "all") -> dict:
    import platform
    result = {}

    if section in ("all", "os"):
        result["os"] = {
            "system":   platform.system(),
            "version":  platform.version(),
            "release":  platform.release(),
            "machine":  platform.machine(),
            "hostname": platform.node(),
            "python":   platform.python_version(),
        }

    if section in ("all", "hardware"):
        try:
            import psutil
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            result["hardware"] = {
                "cpu_cores":    psutil.cpu_count(),
                "cpu_percent":  psutil.cpu_percent(interval=1),
                "ram_total_gb": round(vm.total / 1024 ** 3, 1),
                "ram_used_pct": vm.percent,
                "disk_total_gb": round(disk.total / 1024 ** 3, 1),
                "disk_free_gb":  round(disk.free / 1024 ** 3, 1),
            }
        except ImportError:
            result["hardware"] = {"error": "psutil no disponible"}

    if section in ("all", "network"):
        try:
            import socket, psutil
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            connections = [
                {"laddr": f"{c.laddr.ip}:{c.laddr.port}", "status": c.status}
                for c in psutil.net_connections()
                if c.status in ("LISTEN", "ESTABLISHED") and c.laddr
            ][:20]
            result["network"] = {
                "hostname":    hostname,
                "local_ip":    local_ip,
                "connections": connections,
            }
        except Exception as e:
            result["network"] = {"error": str(e)}

    if section in ("all", "processes"):
        result["processes"] = _list_processes(sort_by="memory")

    if section in ("all", "tools"):
        tools_check = ["git", "python", "pip", "node", "npm", "docker",
                       "nmap", "curl", "wget", "wsl", "winget", "choco"]
        result["tools"] = {t: shutil.which(t) is not None for t in tools_check}

    return result
