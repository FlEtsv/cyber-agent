"""
C-07: Registro de cámaras — carga property.json (legado) a cameras_db.

También expone funciones de consulta del contexto de la propiedad:
ubicaciones, zonas por defecto, descripción del espacio vigilado.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROPERTY_JSON = Path("data/property.json")
_DEFAULT_CONTEXT = {
    "address": "Propiedad privada",
    "cameras": [],
    "zones": [],
    "pets": [],
    "description": "Vivienda particular con sistema de vigilancia CyberAgent.",
}


def load_property() -> dict:
    """Carga el contexto de propiedad desde property.json."""
    if _PROPERTY_JSON.exists():
        try:
            return json.loads(_PROPERTY_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("property_context: error leyendo property.json: %s", e)
    return _DEFAULT_CONTEXT.copy()


def migrate_to_db() -> int:
    """
    C-07: Migra las cámaras de property.json a cameras_db.
    Retorna el número de cámaras migradas.
    """
    prop = load_property()
    cameras = prop.get("cameras", [])
    if not cameras:
        return 0

    try:
        from app.security.cameras_db import add_camera, get_all_cameras
        existing = {c["name"] for c in get_all_cameras()}
        migrated = 0
        for cam in cameras:
            name = cam.get("name", "")
            if not name or name in existing:
                continue
            add_camera(
                name=name,
                cam_type=cam.get("type", "interior"),
                source_type=cam.get("source_type", "ha"),
                entity_id=cam.get("entity_id", ""),
                rtsp_url=cam.get("rtsp_url", ""),
                location=cam.get("location", ""),
            )
            migrated += 1
        logger.info("property_context: migradas %d cámaras", migrated)
        return migrated
    except Exception as e:
        logger.error("property_context: error migrando: %s", e)
        return 0


def get_context_for_model(cam_id: str | None = None) -> str:
    """
    Genera un texto de contexto para el modelo (system prompt) describiendo
    la propiedad, las cámaras y las zonas configuradas.
    """
    prop = load_property()
    lines = [
        f"Propiedad: {prop.get('address', 'Vivienda privada')}",
        prop.get("description", ""),
    ]

    if cam_id:
        try:
            from app.security.cameras_db import get_camera_by_name
            cam = get_camera_by_name(cam_id)
            if cam:
                lines.append(f"Cámara activa: {cam['name']} ({cam.get('location', '')})")
                lines.append(f"Tipo: {cam.get('cam_type', 'desconocido')}")
        except Exception:
            pass

    pets = prop.get("pets", [])
    if pets:
        names = ", ".join(p.get("name", "?") for p in pets)
        lines.append(f"Mascotas conocidas: {names}")

    return "\n".join(filter(None, lines))


def save_property(data: dict) -> bool:
    """Guarda el contexto de propiedad en property.json."""
    try:
        _PROPERTY_JSON.parent.mkdir(parents=True, exist_ok=True)
        _PROPERTY_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("property_context: error guardando: %s", e)
        return False
