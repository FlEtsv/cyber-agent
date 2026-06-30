"""
Módulo de SEGURIDAD de CyberAgent. Centralita domótica: cámaras,
eventos, Home Assistant, Telegram, autonomía — con NUESTRO cerebro.

Estado: todo DESACTIVADO por defecto (SECURITY_ENABLED) salvo el notificador de
Telegram, que sí está operativo desde el día 1. La cámara/visión usa Mistral NUBE
(SEC_MISTRAL_API_KEY + Pixtral) para reacción instantánea; el cerebro general es
local. Las claves viven en el gestor de secretos (app.secrets_vault, prefijo SEC_).
"""
import os

# Interruptor maestro del módulo de seguridad (cámaras/eventos/autonomía).
# El notificador de Telegram NO depende de este flag (siempre disponible).
SECURITY_ENABLED = os.environ.get("CYBERAGENT_SECURITY_ENABLED", "0").lower() in ("1", "true", "yes")
