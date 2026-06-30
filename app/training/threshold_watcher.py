"""
AD-01..AD-03: Watcher de umbral por modelo.

Compara el número de ejemplos de alta señal con el umbral configurado en la ModelCard.
Avisa por comms (Telegram) cuando se alcanza el umbral, pero solo una vez por modelo
hasta que el usuario entrena o descarta (AD-03: no spamear).

Integrar en el supervisor para ejecución periódica.
"""
from __future__ import annotations

import threading

_notified: set[str] = set()   # modelos ya avisados
_lock = threading.Lock()


def check_all() -> list[dict]:
    """
    Comprueba todos los modelos registrados.

    Returns:
        Lista de dicts {model_id, count, threshold, ready, notified}
    """
    from app.training.registry import all_ids, get as get_card
    results = []
    for model_id in all_ids():
        result = check(model_id)
        results.append(result)
    return results


def check(model_id: str, notify: bool = True) -> dict:
    """
    Comprueba si un modelo tiene suficientes ejemplos para entrenar.

    Returns:
        {model_id, count, threshold, ready, notified, already_notified}
    """
    from app.training.registry import get as get_card
    from app.training.data_map import get_sources

    card = get_card(model_id)
    if not card:
        return {"model_id": model_id, "error": "not_found"}

    sources = get_sources(model_id)
    count = _count_samples(sources)
    threshold = card.threshold
    ready = count >= threshold

    with _lock:
        already_notified = model_id in _notified

    result = {
        "model_id": model_id,
        "count": count,
        "threshold": threshold,
        "progress_pct": min(100, round(count / threshold * 100)) if threshold > 0 else 0,
        "ready": ready,
        "already_notified": already_notified,
    }

    if ready and not already_notified and notify:
        _send_notification(model_id, count, threshold)
        with _lock:
            _notified.add(model_id)
        result["notified"] = True
    else:
        result["notified"] = False

    return result


def reset_notification(model_id: str) -> None:
    """Resetea el estado de notificación (llamar cuando se entrena o descarta)."""
    with _lock:
        _notified.discard(model_id)


def _count_samples(sources: list[tuple[str, float]]) -> int:
    try:
        from app.training_store import _lock as ts_lock, _conn
        total = 0
        with ts_lock, _conn() as c:
            for kind, min_signal in sources:
                n = c.execute(
                    "SELECT COUNT(*) FROM samples WHERE kind=? AND signal>=?",
                    (kind, min_signal),
                ).fetchone()[0]
                total += n
        return total
    except Exception:
        return 0


def _send_notification(model_id: str, count: int, threshold: int) -> None:
    try:
        from app.comms.router import send_message, WARNING
        send_message(
            title=f"✅ Modelo listo para entrenar: {model_id}",
            body=f"{count}/{threshold} ejemplos recopilados. Ve a Ajustes → Entrenamiento para iniciar.",
            level=WARNING,
            source="training",
        )
    except Exception:
        pass
