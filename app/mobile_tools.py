"""
Mobile device control tools.
Android: via ADB (wireless debugging).
iOS:     via SSH into Termux-like environment (a-Shell / Secure ShellFish) or Shortcuts HTTP.
"""
import subprocess, json, base64, os, re, shutil, time
from pathlib import Path

# ── ADB helper ────────────────────────────────────────────────────────────────

def _adb(*args, timeout=15) -> dict:
    adb = shutil.which("adb") or r"C:\Users\steve\AppData\Local\Android\Sdk\platform-tools\adb.exe"
    if not adb or not Path(adb).exists():
        return {"error": "adb no encontrado. Instala Android SDK Platform Tools o añade adb al PATH."}
    try:
        r = subprocess.run([adb] + list(args), capture_output=True, text=True, timeout=timeout)
        return {"stdout": r.stdout.strip(), "stderr": r.stderr.strip(), "code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout ({timeout}s)"}
    except Exception as e:
        return {"error": str(e)}

def _adb_connected() -> str | None:
    """Returns IP:port of first connected device, or None."""
    r = _adb("devices")
    lines = r.get("stdout", "").splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return None


# ── Android tools ─────────────────────────────────────────────────────────────

MOBILE_TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "mobile_connect",
        "description": "Conecta al móvil Android via ADB inalámbrico. "
                       "El móvil debe tener activado 'Depuración inalámbrica' en Opciones de desarrollador.",
        "parameters": {"type": "object", "properties": {
            "ip":   {"type": "string", "description": "IP del móvil (ej: 192.168.1.50)"},
            "port": {"type": "integer", "description": "Puerto ADB (default 5555)"},
        }, "required": ["ip"]}
    }},
    {"type": "function", "function": {
        "name": "mobile_screenshot",
        "description": "Captura la pantalla actual del móvil Android.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    {"type": "function", "function": {
        "name": "mobile_shell",
        "description": "Ejecuta un comando shell en el móvil Android (como root si disponible).",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "Comando shell de Android"},
        }, "required": ["command"]}
    }},
    {"type": "function", "function": {
        "name": "mobile_tap",
        "description": "Toca una posición en la pantalla del móvil Android.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "integer", "description": "Coordenada X en píxeles"},
            "y": {"type": "integer", "description": "Coordenada Y en píxeles"},
        }, "required": ["x", "y"]}
    }},
    {"type": "function", "function": {
        "name": "mobile_swipe",
        "description": "Desliza en la pantalla del móvil Android.",
        "parameters": {"type": "object", "properties": {
            "x1":       {"type": "integer"},
            "y1":       {"type": "integer"},
            "x2":       {"type": "integer"},
            "y2":       {"type": "integer"},
            "duration": {"type": "integer", "description": "Duración en ms (default 300)"},
        }, "required": ["x1", "y1", "x2", "y2"]}
    }},
    {"type": "function", "function": {
        "name": "mobile_type",
        "description": "Escribe texto en el campo activo del móvil Android.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"},
        }, "required": ["text"]}
    }},
    {"type": "function", "function": {
        "name": "mobile_open_app",
        "description": "Abre una aplicación en el móvil Android por nombre de paquete.",
        "parameters": {"type": "object", "properties": {
            "package": {"type": "string", "description": "Paquete Android (ej: com.whatsapp)"},
        }, "required": ["package"]}
    }},
    {"type": "function", "function": {
        "name": "mobile_list_apps",
        "description": "Lista las aplicaciones instaladas en el móvil Android.",
        "parameters": {"type": "object", "properties": {
            "filter": {"type": "string", "description": "Filtrar por nombre (opcional)"},
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "mobile_status",
        "description": "Devuelve el estado de conexión ADB y la información del móvil conectado.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }},
    # ── iOS via SSH ──────────────────────────────────────────────────────────
    {"type": "function", "function": {
        "name": "ios_shell",
        "description": "Ejecuta un comando en iPhone/iPad via SSH (requiere app a-Shell o iSH instalada "
                       "y servidor SSH activo en el móvil).",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "host":    {"type": "string", "description": "IP del iPhone (ej: 192.168.1.60)"},
            "port":    {"type": "integer", "description": "Puerto SSH (default 22)"},
            "user":    {"type": "string",  "description": "Usuario (default: mobile)"},
        }, "required": ["command", "host"]}
    }},
]

MOBILE_DANGEROUS = {"mobile_shell", "ios_shell", "mobile_open_app"}


def execute_mobile_tool(name: str, args: dict) -> dict:
    try:
        fn = {
            "mobile_connect":    _do_connect,
            "mobile_screenshot": _do_screenshot,
            "mobile_shell":      _do_shell,
            "mobile_tap":        _do_tap,
            "mobile_swipe":      _do_swipe,
            "mobile_type":       _do_type,
            "mobile_open_app":   _do_open_app,
            "mobile_list_apps":  _do_list_apps,
            "mobile_status":     _do_status,
            "ios_shell":         _do_ios_shell,
        }.get(name)
        if fn is None:
            return {"error": f"Herramienta desconocida: {name}"}
        return fn(args)
    except Exception as e:
        return {"error": str(e)}


def _do_connect(args):
    ip   = args["ip"]
    port = int(args.get("port", 5555))
    return _adb("connect", f"{ip}:{port}", timeout=10)

def _do_screenshot(args):
    dev = _adb_connected()
    if not dev:
        return {"error": "No hay ningún dispositivo Android conectado. Usa mobile_connect primero."}
    # Pull screenshot to temp file
    remote = "/sdcard/cyberagent_ss.png"
    _adb("-s", dev, "shell", "screencap", "-p", remote)
    local  = Path(os.environ.get("TEMP", "/tmp")) / "cyberagent_ss.png"
    _adb("-s", dev, "pull", remote, str(local))
    _adb("-s", dev, "shell", "rm", remote)
    if local.exists():
        data = base64.b64encode(local.read_bytes()).decode()
        local.unlink()
        return {"screenshot_base64": data, "format": "png",
                "note": "Imagen capturada del móvil Android"}
    return {"error": "No se pudo capturar la pantalla"}

_SHELL_DANGEROUS = re.compile(r'[;&|`$<>!\\]')

def _do_shell(args):
    dev = _adb_connected()
    if not dev:
        return {"error": "No hay ningún dispositivo Android conectado."}
    cmd = args["command"]
    if _SHELL_DANGEROUS.search(cmd):
        return {"error": "Comando rechazado: contiene caracteres shell peligrosos. "
                         "Usa comandos simples sin ; | & < > $ ` ! \\"}
    return _adb("-s", dev, "shell", cmd, timeout=30)

def _do_tap(args):
    dev = _adb_connected()
    if not dev:
        return {"error": "No hay ningún dispositivo Android conectado."}
    return _adb("-s", dev, "shell", "input", "tap", str(args["x"]), str(args["y"]))

def _do_swipe(args):
    dev = _adb_connected()
    if not dev:
        return {"error": "No hay ningún dispositivo Android conectado."}
    dur = str(args.get("duration", 300))
    return _adb("-s", dev, "shell", "input", "swipe",
                str(args["x1"]), str(args["y1"]), str(args["x2"]), str(args["y2"]), dur)

def _do_type(args):
    dev = _adb_connected()
    if not dev:
        return {"error": "No hay ningún dispositivo Android conectado."}
    # Base64-encode the text to avoid all shell metacharacter issues on Android
    encoded = base64.b64encode(args["text"].encode("utf-8")).decode()
    return _adb("-s", dev, "shell",
                f"echo {encoded} | base64 -d | xargs -0 input text",
                timeout=10)

def _do_open_app(args):
    dev = _adb_connected()
    if not dev:
        return {"error": "No hay ningún dispositivo Android conectado."}
    pkg = args["package"]
    return _adb("-s", dev, "shell", "monkey", "-p", pkg, "-c",
                "android.intent.category.LAUNCHER", "1")

def _do_list_apps(args):
    dev = _adb_connected()
    if not dev:
        return {"error": "No hay ningún dispositivo Android conectado."}
    r = _adb("-s", dev, "shell", "pm", "list", "packages", timeout=20)
    pkgs = [l.replace("package:", "") for l in r.get("stdout", "").splitlines()]
    f = args.get("filter", "").lower()
    if f:
        pkgs = [p for p in pkgs if f in p.lower()]
    return {"packages": pkgs, "count": len(pkgs)}

def _do_status(args):
    dev = _adb_connected()
    if not dev:
        return {"connected": False, "message": "No hay dispositivo Android conectado via ADB."}
    r = _adb("-s", dev, "shell", "getprop", "ro.product.model")
    model = r.get("stdout", "desconocido")
    batt  = _adb("-s", dev, "shell", "dumpsys", "battery", timeout=5)
    return {"connected": True, "device": dev, "model": model, "battery_info": batt.get("stdout", "")}

def _do_ios_shell(args):
    host = args["host"]
    port = int(args.get("port", 22))
    user = args.get("user", "mobile")
    cmd  = args["command"]
    ssh  = shutil.which("ssh")
    if not ssh:
        return {"error": "SSH no disponible en el PC"}
    try:
        r = subprocess.run(
            [ssh, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
             "-p", str(port), f"{user}@{host}", cmd],
            capture_output=True, text=True, timeout=30,
        )
        return {"stdout": r.stdout.strip(), "stderr": r.stderr.strip(), "code": r.returncode}
    except Exception as e:
        return {"error": str(e)}
