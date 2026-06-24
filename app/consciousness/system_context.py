"""
Detecta el contexto del sistema en el que corre el agente e inyecta
información actualizada en el system prompt de cada sesión.
"""
import platform, os, shutil, socket
from datetime import datetime

PERSONALITY_PROFILES = {
    "general": {
        "label": "Asistente general",
        "prompt": (
            "Perfil activo: Asistente general. Responde de forma directa, practica y equilibrada. "
            "Elige herramientas solo cuando aporten valor claro."
        ),
    },
    "offensive": {
        "label": "Hacker ofensivo",
        "prompt": (
            "Perfil activo: Hacker ofensivo. Prioriza reconocimiento, enumeracion, analisis de superficie "
            "y validacion tecnica solo en sistemas autorizados. Mantiene intactas todas las politicas de "
            "seguridad, permisos y aprobacion de herramientas."
        ),
    },
    "defensive": {
        "label": "Analista defensivo",
        "prompt": (
            "Perfil activo: Analista defensivo. Prioriza deteccion, hardening, respuesta a incidentes, "
            "triage de logs, contencion y recomendaciones verificables. Mantiene intactas todas las "
            "politicas de seguridad, permisos y aprobacion de herramientas."
        ),
    },
}


def get_personality_profile(profile_id: str) -> dict:
    return PERSONALITY_PROFILES.get(profile_id) or PERSONALITY_PROFILES["general"]


def get_personality_labels() -> list[tuple[str, str]]:
    return [(key, value["label"]) for key, value in PERSONALITY_PROFILES.items()]


def get_system_context() -> str:
    lines = [
        "── CONTEXTO DEL SISTEMA ──",
        f"OS:        {platform.system()} {platform.release()} ({platform.version()[:60]})",
        f"Arch:      {platform.machine()}",
        f"Hostname:  {platform.node()}",
        f"Python:    {platform.python_version()}",
        f"Fecha:     {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Usuario:   {_get_user()}",
        f"CWD:       {os.getcwd()}",
    ]

    # RAM + CPU
    try:
        import psutil
        vm  = psutil.virtual_memory()
        cpu = psutil.cpu_count()
        lines.append(f"CPU:       {cpu} núcleos · {psutil.cpu_percent(interval=0):.0f}% uso")
        lines.append(f"RAM:       {vm.total/1024**3:.1f} GB total · {vm.percent}% usada")
    except ImportError:
        pass

    # Tools disponibles
    tools = [t for t in ["git","python","pip","node","npm","docker","nmap","curl","wget","wsl","winget"] if shutil.which(t)]
    lines.append(f"Herramientas: {', '.join(tools) or 'ninguna detectada'}")

    # Red
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        lines.append(f"IP local:  {local_ip}")
    except Exception:
        pass

    # Admin?
    lines.append(f"Permisos:  {'Administrador' if _is_admin() else 'Usuario normal'}")
    lines.append("──────────────────────────")
    return "\n".join(lines)


def _get_user() -> str:
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USERNAME") or os.environ.get("USER") or "desconocido"


def _is_admin() -> bool:
    try:
        if platform.system() == "Windows":
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.getuid() == 0
    except Exception:
        return False


def build_system_prompt(base_prompt: str, personality: str = "general") -> str:
    """Construye el system prompt con contexto del sistema y auto-conciencia."""
    ctx = get_system_context()
    profile = get_personality_profile(personality)
    profile_block = (
        "\n\n--- PERFIL DE RESPUESTA ---\n"
        f"{profile['prompt']}\n"
        "Este perfil no modifica filtros, permisos ni politicas de seguridad."
    )
    try:
        from app.consciousness.self_awareness import get_architecture_block
        arch = "\n\n" + get_architecture_block()
    except Exception:
        arch = ""
    return f"{base_prompt}{profile_block}\n\n{ctx}{arch}"
