"""
AC-01..AC-04: Dataset builder por modelo.

Construye datasets de entrenamiento desde training_store, con:
  - Filtrado por kind + señal mínima (AC-01)
  - Dedup + balanceo entre kinds (AC-02)
  - Split train/eval con holdout (AC-04)
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any


def _hash_sample(instruction: str, response: str) -> str:
    return hashlib.md5(f"{instruction[:200]}|{response[:200]}".encode()).hexdigest()


def build(
    model_id: str,
    min_signal: float | None = None,
    max_samples: int = 5_000,
    dedup: bool = True,
    balance_kinds: bool = True,
    eval_ratio: float = 0.1,
    seed: int = 42,
) -> dict[str, list[dict]]:
    """
    Construye y divide el dataset para model_id.

    Returns:
        {"train": [...], "eval": [...], "stats": {...}}
    """
    from app.training.data_map import get_sources
    from app.training_store import _lock, _conn

    sources = get_sources(model_id)
    if not sources:
        return {"train": [], "eval": [], "stats": {"error": f"No hay fuentes para {model_id}"}}

    # Recopilar muestras de cada fuente
    per_kind: dict[str, list[dict]] = {}
    with _lock, _conn() as c:
        for kind, kind_min_signal in sources:
            eff_min = kind_min_signal if min_signal is None else max(min_signal, kind_min_signal)
            rows = c.execute(
                "SELECT * FROM samples WHERE kind=? AND signal>=? ORDER BY signal DESC LIMIT ?",
                (kind, eff_min, max_samples),
            ).fetchall()
            per_kind[kind] = [dict(r) for r in rows]

    # AC-02: dedup
    if dedup:
        seen: set[str] = set()
        for kind in per_kind:
            deduped = []
            for s in per_kind[kind]:
                h = _hash_sample(s["instruction"], s["response"])
                if h not in seen:
                    seen.add(h)
                    deduped.append(s)
            per_kind[kind] = deduped

    # AC-02: balanceo (limitar cada kind al mismo número de ejemplos)
    if balance_kinds and len(per_kind) > 1:
        min_count = min(len(v) for v in per_kind.values() if v)
        cap = max(50, min_count)
        for kind in per_kind:
            random.seed(seed)
            if len(per_kind[kind]) > cap:
                per_kind[kind] = random.sample(per_kind[kind], cap)

    # Unir y mezclar
    all_samples = [s for samples in per_kind.values() for s in samples]
    random.seed(seed)
    random.shuffle(all_samples)
    all_samples = all_samples[:max_samples]

    # AC-04: split train/eval
    n_eval = max(1, int(len(all_samples) * eval_ratio))
    eval_samples = all_samples[:n_eval]
    train_samples = all_samples[n_eval:]

    stats = {
        "total": len(all_samples),
        "train": len(train_samples),
        "eval": len(eval_samples),
        "by_kind": {k: len(v) for k, v in per_kind.items()},
    }

    return {"train": train_samples, "eval": eval_samples, "stats": stats}


def export_jsonl(
    samples: list[dict],
    path: Path | str,
    system_prompt: str = "",
) -> Path:
    """AC-05: Exporta muestras a JSONL en formato chat."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for s in samples:
            instruction = s.get("instruction") or ""
            response = s.get("response") or ""
            signal = float(s.get("signal") or 0.0)
            weight = max(0.0, (signal + 1.0) / 2.0)
            meta = json.loads(s.get("meta") or "{}")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            # Intentar separar system del user si hay patrón
            if "\n\nUSER: " in instruction:
                sys_part, user_part = instruction.split("\n\nUSER: ", 1)
                if not system_prompt:
                    messages.append({"role": "system", "content": sys_part.strip()})
                messages.append({"role": "user", "content": user_part.strip()})
            elif instruction.strip():
                messages.append({"role": "user", "content": instruction.strip()})
            if response.strip():
                messages.append({"role": "assistant", "content": response.strip()})
            if len(messages) >= 2:
                entry: dict[str, Any] = {"messages": messages, "weight": round(weight, 4),
                                          "kind": s.get("kind", "")}
                if meta.get("model"):
                    entry["model"] = meta["model"]
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return out
