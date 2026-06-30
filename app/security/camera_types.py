"""
R-01 + S-01: Tipos de cámara — exterior e interior.

Cada tipo de cámara hereda de CameraType y define:
- Eventos esperados
- Niveles de alerta por defecto
- Contexto para el modelo de visión
- Actuadores recomendados
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CameraKind = Literal["interior", "exterior"]


@dataclass
class CameraType:
    kind: CameraKind
    expected_events: list[str] = field(default_factory=list)
    default_alert_level: str = "MEDIA"
    vision_context: str = ""
    recommended_actuators: list[str] = field(default_factory=list)
    analyze_persons: bool = False
    analyze_animals: bool = True
    deterrence_enabled: bool = True

    def get_system_prompt_fragment(self) -> str:
        lines = [
            f"Tipo de cámara: {self.kind}.",
            f"Eventos esperados: {', '.join(self.expected_events)}.",
        ]
        if self.vision_context:
            lines.append(self.vision_context)
        if self.analyze_persons:
            lines.append("Priorizar análisis de personas: vestimenta, acciones, aspectos físicos.")
        if self.analyze_animals:
            lines.append("Detectar y hacer seguimiento de animales (especialmente gatos).")
        return " ".join(lines)


# ── R-01: Exterior ────────────────────────────────────────────────────────────

class ExteriorCamera(CameraType):
    """
    Cámara exterior: puerta principal, jardín, garaje, accesos.
    Vigilancia de intrusión, merodeo, vehículos sospechosos.
    """

    def __init__(self, location: str = "exterior"):
        super().__init__(
            kind="exterior",
            expected_events=["intrusion", "loitering", "vehicle", "person", "motion"],
            default_alert_level="ALTA",
            vision_context=(
                f"Cámara exterior en {location}. "
                "Vigilar: intrusos, merodeo, vehículos desconocidos, comportamiento sospechoso. "
                "Si hay personas, describir vestimenta, complexión, acciones y dirección de movimiento."
            ),
            recommended_actuators=["system_speaker", "ha_light", "ha_siren"],
            analyze_persons=True,
            analyze_animals=False,
            deterrence_enabled=True,
        )


# ── S-01: Interior ────────────────────────────────────────────────────────────

class InteriorCamera(CameraType):
    """
    Cámara interior: habitaciones, salón, cocina.
    Vigilancia de mascotas + anomalías en la escena.
    NO vigila personas (privacidad).
    """

    def __init__(self, location: str = "interior"):
        super().__init__(
            kind="interior",
            expected_events=["cat_detected", "anomaly", "danger_zone", "disorder", "fire_smoke"],
            default_alert_level="BAJA",
            vision_context=(
                f"Cámara interior en {location}. "
                "Vigilar mascotas (gatos principalmente), zonas peligrosas (cocina, enchufes), "
                "desorden, roturas o anomalías. "
                "NO reportar presencia humana normal — foco en el bienestar de los gatos."
            ),
            recommended_actuators=["system_speaker", "bt_speaker"],
            analyze_persons=False,
            analyze_animals=True,
            deterrence_enabled=False,
        )


# ── Factory ───────────────────────────────────────────────────────────────────

def camera_type_for(kind: CameraKind, location: str = "") -> CameraType:
    """Devuelve el objeto CameraType correcto para el kind dado."""
    if kind == "exterior":
        return ExteriorCamera(location=location or "exterior")
    return InteriorCamera(location=location or "interior")


def context_for_camera(cam: dict) -> str:
    """Genera el contexto completo de cámara para el modelo de visión."""
    ct = camera_type_for(cam.get("kind", "interior"), cam.get("location", ""))
    base = ct.get_system_prompt_fragment()
    # Añadir contexto personalizado si existe
    extra = cam.get("context", "") or cam.get("location", "")
    if extra and extra not in base:
        base += f" Contexto adicional: {extra}"
    return base
