"""
Contador de consumo de Mistral (tokens y coste).

Unifica los dos scripts sueltos previos (`mistral_cost_tracker.py` y
`mistral_monitor.py`) y los conecta de verdad al flujo: cada llamada real a
Mistral (tool `mistral_consult` y el streaming del cerebro) registra aquí su
uso. Persiste en CSV y mantiene un total de sesión consultable en caliente.

Tarifas por millón de tokens (USD, aprox. 2026). Ajustables por entorno con
CYBERAGENT_MISTRAL_PRICING="modelo:in/out,modelo:in/out".
"""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime, date
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_FILE = _DATA_DIR / "mistral_usage.csv"

# (input, output) USD por millón de tokens
_DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    "mistral-medium-latest": (0.40, 2.00),
    "mistral-medium":        (0.40, 2.00),
    "mistral-large-latest":  (2.00, 6.00),
    "mistral-large":         (2.00, 6.00),
    "mistral-small-latest":  (0.10, 0.30),
    "magistral-medium-latest": (0.40, 2.00),
    "pixtral-large-latest":  (2.00, 6.00),
    "codestral-latest":      (0.30, 0.90),
    "codestral":             (0.30, 0.90),
    "mistral-ocr-latest":    (1.00, 0.00),   # OCR: ~$1 por 1000 páginas (aprox)
    "mistral-embed":         (0.10, 0.00),
    "mistral-studio":        (0.40, 2.00),   # connectors: estimado (tienen recargos por uso)
}
_FALLBACK = (0.40, 2.00)

_lock = threading.Lock()
_session = {"input": 0, "output": 0, "cost": 0.0, "calls": 0}
_listeners = []   # callbacks fn(resumen_sesion) llamados tras cada registro real


def add_listener(fn) -> None:
    """Registra un callback fn(resumen_sesion) invocado tras CADA llamada real a
    Mistral. Permite refrescar la UI aprovechando la llamada, sin sondear."""
    if fn not in _listeners:
        _listeners.append(fn)


def _pricing_for(model: str) -> tuple[float, float]:
    table = dict(_DEFAULT_PRICING)
    raw = os.getenv("CYBERAGENT_MISTRAL_PRICING", "").strip()
    if raw:
        for part in raw.split(","):
            try:
                name, rates = part.split(":")
                i, o = rates.split("/")
                table[name.strip()] = (float(i), float(o))
            except Exception:
                continue
    m = (model or "").strip().lower()
    if m in table:
        return table[m]
    for key, val in table.items():
        if m.startswith(key):
            return val
    return _FALLBACK


def cost_of(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = _pricing_for(model)
    return (input_tokens / 1_000_000) * pin + (output_tokens / 1_000_000) * pout


def _ensure_csv() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["timestamp", "model", "input_tokens", "output_tokens",
                 "cost_usd", "context"]
            )


def log_usage(model: str, input_tokens: int, output_tokens: int,
              context: str = "agent") -> float:
    """Registra una llamada a Mistral. Devuelve el coste de esa llamada (USD)."""
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    if input_tokens <= 0 and output_tokens <= 0:
        return 0.0
    cost = cost_of(model, input_tokens, output_tokens)
    try:
        with _lock:
            _ensure_csv()
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    model, input_tokens, output_tokens, f"{cost:.6f}", context,
                ])
            _session["input"] += input_tokens
            _session["output"] += output_tokens
            _session["cost"] += cost
            _session["calls"] += 1
            snapshot = dict(_session)
    except Exception:
        return cost
    # Notifica a los listeners (UI) tras cada llamada REAL — sin polling.
    for fn in list(_listeners):
        try:
            fn(snapshot)
        except Exception:
            pass
    return cost


def session_summary() -> dict:
    with _lock:
        return dict(_session)


def get_summary(scope: str = "all") -> dict:
    """Resumen acumulado del CSV. scope: 'all', 'today' o 'month'."""
    totals = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0}
    if not LOG_FILE.exists():
        return totals
    prefix = date.today().isoformat() if scope == "today" else date.today().strftime("%Y-%m")
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if scope in ("today", "month") and not str(row.get("timestamp", "")).startswith(prefix):
                    continue
                totals["input_tokens"] += int(row.get("input_tokens") or 0)
                totals["output_tokens"] += int(row.get("output_tokens") or 0)
                totals["cost_usd"] += float(row.get("cost_usd") or 0.0)
                totals["calls"] += 1
    except Exception:
        pass
    return totals


def format_summary(scope: str = "all") -> str:
    s = get_summary(scope)
    return (
        f"Mistral {scope}: {s['calls']} llamadas · "
        f"{s['input_tokens']:,} in / {s['output_tokens']:,} out tokens · "
        f"${s['cost_usd']:.4f}"
    )


if __name__ == "__main__":
    print(format_summary("today"))
    print(format_summary("all"))
