"""
B-06: Teclados inline para el bot de Telegram.

Devuelve dicts compatibles con la API de Telegram (reply_markup).
"""
from __future__ import annotations


def security_keyboard(cam_id: str = "", event_id: str = "") -> dict:
    """Teclado para alertas de seguridad."""
    row1 = [
        {"text": "✅ Confirmar", "callback_data": f"sec:confirm:{event_id}"},
        {"text": "❌ Ignorar", "callback_data": f"sec:ignore:{event_id}"},
    ]
    row2 = [
        {"text": "📷 Ver cámara", "callback_data": f"sec:cam:{cam_id}"},
        {"text": "🔕 Silenciar 1h", "callback_data": f"sec:mute:60:{cam_id}"},
    ]
    row3 = [
        {"text": "⬆️ Escalar", "callback_data": f"sec:escalate:{event_id}"},
        {"text": "🔊 Disuadir", "callback_data": f"sec:deter:{cam_id}"},
    ]
    return {"inline_keyboard": [row1, row2, row3]}


def agent_keyboard(tool_name: str = "", run_id: str = "") -> dict:
    """Teclado para aprobaciones de herramientas del agente."""
    row1 = [
        {"text": "✅ Aprobar", "callback_data": f"agent:approve:{run_id}"},
        {"text": "❌ Rechazar", "callback_data": f"agent:reject:{run_id}"},
    ]
    row2 = [
        {"text": "📋 Detalle", "callback_data": f"agent:detail:{run_id}"},
        {"text": "🔄 Reintentar", "callback_data": f"agent:retry:{run_id}"},
    ]
    return {"inline_keyboard": [row1, row2]}


def autonomy_keyboard(current_mode: str = "manual") -> dict:
    modes = ["manual", "operativa", "alto-impacto"]
    row = [
        {"text": f"{'✓ ' if m == current_mode else ''}{m}", "callback_data": f"aut:set:{m}"}
        for m in modes
    ]
    return {"inline_keyboard": [row]}


def snapshot_keyboard(cam_id: str) -> dict:
    return {"inline_keyboard": [[
        {"text": "📷 Nuevo snapshot", "callback_data": f"cam:snap:{cam_id}"},
        {"text": "🎥 Clip 30s", "callback_data": f"cam:clip:{cam_id}"},
    ]]}
