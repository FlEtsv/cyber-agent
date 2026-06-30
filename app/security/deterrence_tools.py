"""
AW-05 + AM-03 + AM-08: Tools de disuasión para el agente.

Expone las acciones de disuasión como tools que el agente puede invocar.
Integradas con el sistema de aprobaciones (DANGEROUS) para niveles altos.
"""
from __future__ import annotations

import os


def _security_enabled() -> bool:
    return os.environ.get("SECURITY_ENABLED", "0") == "1"


def deter_warn(cam_id: str) -> dict:
    """
    AW-05: Nivel 2 — sonido de aviso por el altavoz del sistema.
    Tool del agente: requiere aprobación si SECURITY_ENABLED=0.
    """
    if not _security_enabled():
        return {"ok": False, "error": "SECURITY_ENABLED=0. Módulo de seguridad desactivado."}
    from app.security.deterrence import trigger
    ok = trigger(cam_id, threat_score=0.6)
    return {"ok": ok, "cam_id": cam_id, "action": "audio_warn"}


def deter_sound(cam_id: str, scenario: str = "warning") -> dict:
    """
    AW-05: Reproducir sonido de escenario específico (sirena/ladrido/alarma).
    """
    if not _security_enabled():
        return {"ok": False, "error": "SECURITY_ENABLED=0"}
    from app.security.audio.library import play_scenario
    ok = play_scenario(scenario)
    return {"ok": ok, "cam_id": cam_id, "scenario": scenario}


def deter_narrate(cam_id: str, text: str = "") -> dict:
    """
    AW-05 + AU-06: Nivel 3 — narrar descripción de lo que ve la IA.
    """
    if not _security_enabled():
        return {"ok": False, "error": "SECURITY_ENABLED=0"}
    narration = text or "Atención. Presencia detectada en zona vigilada. Se está grabando."
    from app.security.audio.live_narrate import narrate
    ok = narrate(narration, force=True)
    return {"ok": ok, "cam_id": cam_id, "text": narration}


def deter_light(cam_id: str) -> dict:
    """
    AW-05: Nivel 4 — encender luz (via HA si está disponible).
    Requiere SECURITY_ENABLED=1 + HA configurado.
    """
    if not _security_enabled():
        return {"ok": False, "error": "SECURITY_ENABLED=0"}
    try:
        from app.security.ha_tools import ha_control
        result = ha_control("light_ir", "on")
        return {"ok": True, "cam_id": cam_id, "ha_result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cats_separate_sound(cam_id: str = "") -> dict:
    """
    AM-03: Sonido para separar gatos (frecuencia alta inofensiva).
    """
    if not _security_enabled():
        return {"ok": False, "error": "SECURITY_ENABLED=0"}
    from app.security.audio.library import play_scenario
    ok = play_scenario("cats_separate")
    return {"ok": ok, "cam_id": cam_id, "scenario": "cats_separate"}
