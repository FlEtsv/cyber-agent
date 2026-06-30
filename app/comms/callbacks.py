"""
AP-04..AP-06: Handler de callback_query de Telegram.

Procesa los botones pulsados en inline keyboards:
- sec:confirm / sec:ignore / sec:view_cam / sec:mute / sec:escalate / sec:deter
- agent:approve / agent:reject / agent:detail / agent:retry

Las acciones peligrosas requieren confirmación adicional (AP-05).
Los ACKs de seguridad alimentan training_store (AP-06).
"""
from __future__ import annotations


def handle_callback(callback_data: str, from_user_id: int) -> dict:
    """
    AP-04: Despacha el callback a la acción correspondiente.

    Args:
        callback_data: string del callback_data del botón pulsado
        from_user_id: Telegram user_id del que pulsó

    Returns:
        dict con 'answer_text' (respuesta al callback) y 'edit_text' opcional
    """
    try:
        parts = callback_data.split(":")
        ns = parts[0]  # 'sec' o 'agent'

        if ns == "sec":
            return _handle_security(parts, from_user_id)
        elif ns == "agent":
            return _handle_agent(parts, from_user_id)
        else:
            return {"answer_text": "Acción desconocida"}
    except Exception as e:
        return {"answer_text": f"Error: {e}"}


def _handle_security(parts: list[str], from_user_id: int) -> dict:
    action = parts[1] if len(parts) > 1 else ""
    event_id = parts[2] if len(parts) > 2 else ""
    cam_id = parts[2] if len(parts) > 2 else ""

    if action == "confirm":
        _record_security_feedback(event_id, correct=True)
        return {"answer_text": "✅ Evento confirmado", "edit_text": "✅ Confirmado por operador"}

    elif action == "ignore":
        _record_security_feedback(event_id, correct=False)
        return {"answer_text": "🔕 Evento ignorado", "edit_text": "🔕 Ignorado por operador"}

    elif action == "view_cam":
        return {"answer_text": f"📷 Cargando cámara {cam_id}…", "cam_id": cam_id}

    elif action == "mute":
        secs = int(parts[2]) if len(parts) > 2 else 3600
        cam_id = parts[3] if len(parts) > 3 else ""
        return {"answer_text": f"⏱️ Silenciado {secs//60} min", "mute_cam": cam_id, "mute_secs": secs}

    elif action == "escalate":
        return {"answer_text": "🔺 Escalando…", "edit_text": "🔺 Escalado a nivel superior"}

    elif action == "deter":
        # AP-05: acción peligrosa — requiere confirmar
        return {
            "answer_text": "🔊 ¿Confirmar disuasión?",
            "confirm_action": f"sec:deter_confirm:{cam_id}",
        }

    return {"answer_text": "OK"}


def _handle_agent(parts: list[str], from_user_id: int) -> dict:
    action = parts[1] if len(parts) > 1 else ""
    run_id = parts[2] if len(parts) > 2 else ""

    if action == "approve":
        return {"answer_text": "✅ Aprobado", "edit_text": "✅ Aprobado por operador", "run_id": run_id, "approved": True}

    elif action == "reject":
        return {"answer_text": "❌ Rechazado", "edit_text": "❌ Rechazado por operador", "run_id": run_id, "approved": False}

    elif action == "detail":
        return {"answer_text": "🔍 Consulta detalle en la app"}

    elif action == "retry":
        return {"answer_text": "🔄 Reintentando…", "retry": run_id}

    return {"answer_text": "OK"}


def _record_security_feedback(event_id: str, correct: bool):
    """AP-06: Feedback de seguridad → training_store."""
    try:
        from app.security.feedback import record_detection_feedback
        record_detection_feedback(
            event_description=f"Callback event_id={event_id}",
            model_decision="alert",
            correct=correct,
            false_positive=not correct,
            false_negative=False,
        )
    except Exception:
        pass
