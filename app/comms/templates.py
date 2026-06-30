"""
AS-04: Plantillas de mensaje por tipo (formato/emoji/campos).

Cada plantilla devuelve un dict listo para `router.send_message`:
{title, body, level, source, emoji, keyboard}. Centraliza el formato para que
todas las notificaciones tengan el mismo estilo (ver docs/COMMS_PLAN.md).
Las plantillas son editables: se pueden sobreescribir vía `register`.
"""
from __future__ import annotations

from app.comms.levels import Severity


def _esc(s) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ctx_line(camera: str = "", when: str = "", zone: str = "", extra: str = "") -> str:
    parts = []
    if camera:
        parts.append(f"📷 {camera}")
    if when:
        parts.append(when)
    if zone:
        parts.append(f"zona {zone}")
    if extra:
        parts.append(extra)
    return " · ".join(parts)


# ── Plantillas (devuelven kwargs para router.send_message) ────────────────────
def threat_exterior(desc: str, camera: str = "", when: str = "", zone: str = "") -> dict:
    body = _esc(desc)
    ctx = _ctx_line(camera, when, zone)
    if ctx:
        body += f"\n{ctx}"
    return {"title": "AMENAZA EXTERIOR", "body": body, "level": int(Severity.CRITICA),
            "source": "security", "emoji": "🔴", "keyboard": "threat_exterior"}


def pet_danger(pet: str, desc: str, camera: str = "", when: str = "") -> dict:
    body = _esc(desc)
    ctx = _ctx_line(camera, when)
    if ctx:
        body += f"\n{ctx}"
    return {"title": f"{_esc(pet)} en peligro", "body": body, "level": int(Severity.ALTA),
            "source": "security", "emoji": "🐈", "keyboard": "pet_danger"}


def camera_warning(desc: str, camera: str = "", when: str = "") -> dict:
    body = _esc(desc)
    ctx = _ctx_line(camera, when)
    if ctx:
        body += f"\n{ctx}"
    return {"title": "Aviso de cámara", "body": body, "level": int(Severity.MEDIA),
            "source": "security", "emoji": "🛡️", "keyboard": "camera"}


def agent_done(task: str, detail: str = "") -> dict:
    return {"title": "Tarea completada", "body": f"{_esc(task)}" + (f"\n{_esc(detail)}" if detail else ""),
            "level": int(Severity.MEDIA), "source": "agent", "emoji": "🔔",
            "keyboard": "agent_notify"}


def agent_approval(action: str, detail: str = "") -> dict:
    return {"title": "Aprobación pendiente", "body": f"{_esc(action)}" + (f"\n{_esc(detail)}" if detail else ""),
            "level": int(Severity.ALTA), "source": "agent", "emoji": "⚠️",
            "keyboard": "agent_approval"}


def system_error(what: str, detail: str = "", critical: bool = False) -> dict:
    return {"title": "Error" + (" crítico" if critical else ""),
            "body": f"{_esc(what)}" + (f"\n{_esc(detail)}" if detail else ""),
            "level": int(Severity.CRITICA if critical else Severity.BAJA),
            "source": "system", "emoji": "🔴" if critical else "⚙️", "keyboard": "system"}


def model_ready(model_id: str, count: int, threshold: int) -> dict:
    return {"title": "Modelo listo para entrenar",
            "body": f"<b>{_esc(model_id)}</b> alcanzó {count}/{threshold} ejemplos.\n"
                    "Ve a Ajustes → Entrenamiento para iniciarlo.",
            "level": int(Severity.MEDIA), "source": "training", "emoji": "🎓",
            "keyboard": None}


def digest(title: str, items: list[str]) -> dict:
    body = "\n".join(f"• {_esc(i)}" for i in items)
    return {"title": title, "body": body, "level": int(Severity.PERIODICA),
            "source": "digest", "emoji": "📊", "keyboard": None}


# Registro editable (AS-04): permite sobreescribir una plantilla en caliente.
_OVERRIDES: dict = {}


def register(name: str, fn) -> None:
    _OVERRIDES[name] = fn


def render(name: str, *args, **kwargs) -> dict:
    fn = _OVERRIDES.get(name) or globals().get(name)
    if not callable(fn):
        raise ValueError(f"plantilla desconocida: {name}")
    return fn(*args, **kwargs)


def send(name: str, *args, **kwargs) -> dict:
    """Renderiza la plantilla y la envía por el router de comms."""
    data = render(name, *args, **kwargs)
    from app.comms.router import send_message
    return send_message(data["title"], data.get("body", ""),
                        level=data.get("level"), source=data.get("source"),
                        emoji=data.get("emoji"))
