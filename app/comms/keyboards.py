"""
AP-01..AP-03: Inline keyboards para mensajes de Telegram.

Genera las estructuras de botones inline para:
- Alertas de seguridad (confirmar/ignorar/ver/silenciar/escalar/disuadir)
- Acciones del agente (aprobar/rechazar/detalle/reintentar)
"""
from __future__ import annotations


def security_keyboard(cam_id: str = "", event_id: str = "") -> list[list[dict]]:
    """
    AP-02: Teclado para alertas de seguridad.
    Botones: Confirmar · Ignorar · Ver cámara · Silenciar 1h · Escalar · Disuadir
    """
    return [
        [
            {"text": "✅ Confirmar", "callback_data": f"sec:confirm:{event_id}"},
            {"text": "🔕 Ignorar", "callback_data": f"sec:ignore:{event_id}"},
        ],
        [
            {"text": "📷 Ver cámara", "callback_data": f"sec:view_cam:{cam_id}"},
            {"text": "⏱️ Silenciar 1h", "callback_data": f"sec:mute:3600:{cam_id}"},
        ],
        [
            {"text": "🔺 Escalar", "callback_data": f"sec:escalate:{event_id}"},
            {"text": "🔊 Disuadir", "callback_data": f"sec:deter:{cam_id}"},
        ],
    ]


def agent_keyboard(tool_name: str = "", run_id: str = "") -> list[list[dict]]:
    """
    AP-03: Teclado para acciones del agente.
    Botones: Aprobar · Rechazar · Ver detalle · Reintentar
    """
    return [
        [
            {"text": "✅ Aprobar", "callback_data": f"agent:approve:{run_id}"},
            {"text": "❌ Rechazar", "callback_data": f"agent:reject:{run_id}"},
        ],
        [
            {"text": "🔍 Ver detalle", "callback_data": f"agent:detail:{run_id}"},
            {"text": "🔄 Reintentar", "callback_data": f"agent:retry:{run_id}"},
        ],
    ]


def to_telegram_markup(rows: list[list[dict]]) -> dict:
    """Convierte las filas de botones al formato InlineKeyboardMarkup de Telegram."""
    return {
        "inline_keyboard": rows,
    }
