"""
Contador de tokens del modelo LOCAL y de DINERO AHORRADO frente a la nube.

Cada generación local (Ollama) registra aquí sus tokens (prompt + salida). El
"ahorro" se calcula con la tarifa de un modelo de nube de referencia: por defecto
`mistral-small-latest`, que es EL MISMO modelo que corre en local (Mistral Small
24B) → comparación honesta de "lo que habrías pagado en la nube".

Persiste en CSV y mantiene un total de sesión consultable en caliente. Mismo
patrón que `mistral_usage` (listeners para refrescar la UI sin polling).

Configurable por entorno:
  CYBERAGENT_SAVINGS_REF_MODEL  (default mistral-small-latest)
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime, date
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_FILE = _DATA_DIR / "local_usage.csv"

# Modelo de nube de referencia para valorar el ahorro (mismo modelo = honesto).
REF_MODEL = os.getenv("CYBERAGENT_SAVINGS_REF_MODEL", "mistral-small-latest")

_lock = threading.Lock()
_session = {"input": 0, "output": 0, "saved": 0.0, "calls": 0}
_listeners: list = []


def add_listener(fn) -> None:
    """Callback fn(resumen_sesion) llamado tras CADA generación local."""
    if fn not in _listeners:
        _listeners.append(fn)


def _saved_for(input_tokens: int, output_tokens: int) -> float:
    """Lo que habrían costado estos tokens en la nube (modelo de referencia)."""
    try:
        from app.mistral_usage import cost_of
        return cost_of(REF_MODEL, input_tokens, output_tokens)
    except Exception:
        # Tarifa de respaldo equivalente a mistral-small-latest ($0.10/$0.30 por Mtok)
        return (input_tokens / 1_000_000) * 0.10 + (output_tokens / 1_000_000) * 0.30


def _ensure_csv() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["timestamp", "model", "input_tokens", "output_tokens",
                 "saved_usd", "context"]
            )


def log_local(input_tokens: int, output_tokens: int,
              model: str = "local", context: str = "agent") -> float:
    """Registra una generación local. Devuelve el ahorro de esa llamada (USD)."""
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    if input_tokens <= 0 and output_tokens <= 0:
        return 0.0
    saved = _saved_for(input_tokens, output_tokens)
    try:
        with _lock:
            _ensure_csv()
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    model, input_tokens, output_tokens, f"{saved:.6f}", context,
                ])
            _session["input"] += input_tokens
            _session["output"] += output_tokens
            _session["saved"] += saved
            _session["calls"] += 1
            snapshot = dict(_session)
    except Exception:
        return saved
    for fn in list(_listeners):
        try:
            fn(snapshot)
        except Exception:
            pass
    return saved


def session_summary() -> dict:
    with _lock:
        return dict(_session)


def get_summary(scope: str = "all") -> dict:
    """Resumen acumulado del CSV. scope: 'all' o 'today'."""
    totals = {"input_tokens": 0, "output_tokens": 0, "saved_usd": 0.0, "calls": 0}
    if not LOG_FILE.exists():
        return totals
    today = date.today().isoformat()
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if scope == "today" and not str(row.get("timestamp", "")).startswith(today):
                    continue
                totals["input_tokens"] += int(row.get("input_tokens") or 0)
                totals["output_tokens"] += int(row.get("output_tokens") or 0)
                totals["saved_usd"] += float(row.get("saved_usd") or 0.0)
                totals["calls"] += 1
    except Exception:
        pass
    return totals


def format_savings(scope: str = "all") -> str:
    s = get_summary(scope)
    tot = s["input_tokens"] + s["output_tokens"]
    return (
        f"Ahorrado con modelo local ({scope}): ${s['saved_usd']:.4f} · "
        f"{tot:,} tokens · {s['calls']} generaciones (vs {REF_MODEL} en nube)"
    )


if __name__ == "__main__":
    print(format_savings("today"))
    print(format_savings("all"))
