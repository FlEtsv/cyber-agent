"""
AM-06: Informe diario de gatos — dónde estuvieron, incidencias del día.

Genera un informe resumido de:
  - Actividad de cada gato (zonas visitadas, horas activas)
  - Incidencias (anomalías, disuasiones, alertas)
  - Predicciones correctas vs incorrectas
  - Lugares de descanso detectados

Envía el informe por Telegram y lo persiste en data/reports/.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)
_REPORTS_DIR = Path("data/reports")


def generate_daily_report(date_str: str | None = None) -> dict:
    """
    AM-06: Genera el informe diario de gatos.

    Args:
        date_str: fecha en formato YYYY-MM-DD (hoy por defecto)

    Returns:
        dict con el informe estructurado
    """
    if not date_str:
        date_str = time.strftime("%Y-%m-%d")

    report = {
        "date": date_str,
        "generated_at": time.time(),
        "pets": [],
        "incidents": [],
        "predictions": {},
        "summary": "",
    }

    # Actividad de mascotas
    try:
        from app.security.pets import list_pets
        pets = list_pets()
        for pet in pets:
            pet_data = _pet_activity(pet["id"], pet["name"], date_str)
            report["pets"].append(pet_data)
    except Exception as e:
        logger.warning("report: error obteniendo mascotas: %s", e)

    # Incidencias del día
    try:
        report["incidents"] = _daily_incidents(date_str)
    except Exception as e:
        logger.warning("report: error obteniendo incidencias: %s", e)

    # Estadísticas de predicciones
    try:
        from app.security.predictor import prediction_stats
        report["predictions"] = prediction_stats()
    except Exception as e:
        pass

    # Resumen
    report["summary"] = _build_summary(report)

    # Persistir
    _save_report(report, date_str)

    return report


def _pet_activity(pet_id: int, pet_name: str, date_str: str) -> dict:
    """Actividad de un gato en un día."""
    activity: dict = {"id": pet_id, "name": pet_name, "zones": [], "rest_places": [], "active_hours": []}
    try:
        # Zonas más frecuentadas del día
        from app.security.patterns import typical_zones_by_hour
        zones_seen = set()
        for hour in range(24):
            zones = typical_zones_by_hour("", hour, str(pet_id))
            for z in zones[:1]:
                zones_seen.add(z.get("zone", ""))
        activity["zones"] = list(zones_seen)

        # Lugares de descanso
        from app.security.patterns import rest_places
        rp = rest_places("", str(pet_id), min_visits=1, min_secs=30)
        activity["rest_places"] = [
            {"cx": r.get("cx", 0), "cy": r.get("cy", 0), "visits": r.get("visits", 0)}
            for r in rp[:5]
        ]
    except Exception:
        pass
    return activity


def _daily_incidents(date_str: str) -> list[dict]:
    """Recupera incidencias del día desde events.db."""
    incidents = []
    try:
        import sqlite3
        db = Path("data/events.db")
        if not db.exists():
            return []
        # Timestamp inicio del día
        import datetime
        day = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        ts_start = day.timestamp()
        ts_end = ts_start + 86400
        c = sqlite3.connect(str(db))
        rows = c.execute(
            "SELECT event_type, description, source, ts FROM events WHERE ts >= ? AND ts < ? ORDER BY ts",
            (ts_start, ts_end),
        ).fetchall()
        c.close()
        for r in rows:
            incidents.append({
                "type": r[0],
                "description": r[1],
                "source": r[2],
                "time": time.strftime("%H:%M", time.localtime(r[3])),
            })
    except Exception as e:
        logger.warning("report._daily_incidents: %s", e)
    return incidents


def _build_summary(report: dict) -> str:
    pets = report.get("pets", [])
    incidents = report.get("incidents", [])
    preds = report.get("predictions", {})

    lines = [f"📋 Informe diario — {report['date']}\n"]

    if pets:
        lines.append("🐱 Mascotas:")
        for p in pets:
            zones = ", ".join(p.get("zones", [])[:3]) or "sin datos"
            lines.append(f"  • {p['name']}: zonas visitadas → {zones}")

    if incidents:
        lines.append(f"\n⚠️ Incidencias ({len(incidents)}):")
        for inc in incidents[:5]:
            lines.append(f"  • [{inc['time']}] {inc['type']}: {inc.get('description', '')[:60]}")

    if preds:
        acc = preds.get("accuracy", 0)
        lines.append(f"\n🎯 Predicciones: precisión {acc:.0%}")

    return "\n".join(lines)


def _save_report(report: dict, date_str: str) -> None:
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = _REPORTS_DIR / f"report_{date_str}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def send_daily_report() -> bool:
    """Genera y envía el informe diario por Telegram. Retorna True si se envió."""
    try:
        report = generate_daily_report()
        summary = report.get("summary", "Sin datos disponibles.")
        from app.security.telegram.notify import broadcast
        broadcast(title="📋 Informe diario", body=summary, emoji="📋", silent=True)
        return True
    except Exception as e:
        logger.error("report.send_daily_report: %s", e)
        return False
