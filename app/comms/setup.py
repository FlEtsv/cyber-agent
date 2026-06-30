"""
AN-05: Inicialización del módulo de comunicaciones.

Crea los temas del supergrupo Telegram (si SECURITY_ENABLED y credentials disponibles).
Se llama al arrancar el supervisor.
"""
from __future__ import annotations


def run_setup() -> dict:
    """
    Configura los canales de comunicación al arranque.
    Actualmente: crear topics en el supergrupo Telegram si no existen.
    """
    results = {}

    try:
        from app.secrets_vault import get_secret
        bot_token = get_secret("SEC_TELEGRAM_BOT_TOKEN") or get_secret("TELEGRAM_BOT_TOKEN")
        chat_id = get_secret("SEC_TELEGRAM_CHAT_ID") or get_secret("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            from app.comms.telegram_topics import setup_topics
            result = setup_topics(bot_token, chat_id)
            results["telegram_topics"] = result
        else:
            results["telegram_topics"] = {"ok": False, "error": "no credentials"}
    except Exception as e:
        results["telegram_topics"] = {"ok": False, "error": str(e)}

    return results
