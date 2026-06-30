"""
AF-03: Runner LOCAL QLoRA via PEFT/bitsandbytes (o axolotl como subprocess).

En el estado actual, lanza axolotl como subprocess si está instalado.
Si no, retorna stub con instrucciones.

El adapter resultante se guarda en data/training_runs/{model_id}/adapter/
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Callable


def run(
    model_id: str,
    train_path: Path,
    eval_path: Path,
    hparams: dict,
    progress_cb: Callable[[dict], None] | None = None,
    stop_flag: threading.Event | None = None,
) -> dict:
    """
    Lanza entrenamiento local con QLoRA.

    Returns:
        {"ok": bool, "adapter_path": str | None, "metrics": dict, "error": str}
    """
    from app.training.registry import get as get_card
    card = get_card(model_id)
    if not card:
        return {"ok": False, "error": f"Modelo '{model_id}' no en registry"}

    adapter_dir = train_path.parent / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)

    # Intentar axolotl si está disponible
    result = _try_axolotl(card.base, train_path, eval_path, adapter_dir, hparams,
                          progress_cb, stop_flag)
    if result["ok"]:
        return result

    # Fallback: stub (devuelve instrucciones)
    return {
        "ok": False,
        "error": (
            "axolotl no disponible. Instalar con: pip install axolotl\n"
            f"O usar runner_runpod para {model_id}"
        ),
        "adapter_path": None,
        "metrics": {},
    }


def _try_axolotl(
    base_model: str,
    train_path: Path,
    eval_path: Path,
    out_dir: Path,
    hparams: dict,
    progress_cb,
    stop_flag,
) -> dict:
    try:
        import axolotl  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "axolotl not installed"}

    import yaml, tempfile, os
    config = {
        "base_model": base_model,
        "model_type": "AutoModelForCausalLM",
        "tokenizer_type": "AutoTokenizer",
        "load_in_4bit": True,
        "adapter": "qlora",
        "lora_r": hparams.get("rank", 16),
        "lora_alpha": hparams.get("alpha", 32),
        "lora_dropout": hparams.get("dropout", 0.05),
        "lora_target_linear": True,
        "datasets": [{"path": str(train_path), "type": "chat_template"}],
        "val_set_path": str(eval_path),
        "output_dir": str(out_dir),
        "sequence_len": hparams.get("max_seq_len", 2048),
        "micro_batch_size": hparams.get("batch_size", 2),
        "gradient_accumulation_steps": hparams.get("grad_accum", 8),
        "num_epochs": hparams.get("epochs", 3),
        "learning_rate": hparams.get("lr", 2e-4),
        "optimizer": "adamw_bnb_8bit",
        "lr_scheduler": hparams.get("scheduler", "cosine"),
        "fp16": hparams.get("fp16", True),
        "bf16": hparams.get("bf16", False),
    }

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        cfg_path = f.name

    try:
        proc = subprocess.Popen(
            ["python", "-m", "axolotl.cli.train", cfg_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            line = line.rstrip()
            if progress_cb:
                progress_cb({"log": line})
            if stop_flag and stop_flag.is_set():
                proc.terminate()
                return {"ok": False, "error": "Cancelado", "metrics": {}}

        proc.wait()
        if proc.returncode != 0:
            return {"ok": False, "error": f"axolotl exit {proc.returncode}", "metrics": {}}

        return {"ok": True, "adapter_path": str(out_dir), "metrics": {}}
    finally:
        os.unlink(cfg_path)
