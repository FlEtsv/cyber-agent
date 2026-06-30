"""
AB-04: Hiperparámetros QLoRA por modelo.

Defaults sensatos para fine-tuning con QLoRA en consumer hardware (RTX 3080+).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HParams:
    rank: int = 16              # LoRA rank
    alpha: int = 32             # LoRA alpha
    dropout: float = 0.05       # LoRA dropout
    lr: float = 2e-4            # learning rate
    epochs: int = 3             # epochs de entrenamiento
    batch_size: int = 2         # batch size (limitado por VRAM)
    grad_accum: int = 8         # gradient accumulation steps
    max_seq_len: int = 2048     # longitud máxima de secuencia
    warmup_ratio: float = 0.05  # warmup
    weight_decay: float = 0.01  # weight decay
    scheduler: str = "cosine"   # LR scheduler
    fp16: bool = True           # mixed precision
    bf16: bool = False          # bf16 si la GPU lo soporta


_HPARAMS: dict[str, HParams] = {
    "cyberagent-24b": HParams(rank=16, alpha=32, epochs=3, batch_size=1, grad_accum=16,
                               max_seq_len=2048, lr=1e-4),
    "codestral":       HParams(rank=32, alpha=64, epochs=4, batch_size=2, grad_accum=8,
                               max_seq_len=4096, lr=2e-4),
    "vision-security": HParams(rank=8, alpha=16, epochs=5, batch_size=4, grad_accum=4,
                                max_seq_len=1024, lr=3e-4),
    "tool-router":     HParams(rank=8, alpha=16, epochs=3, batch_size=4, grad_accum=8,
                                max_seq_len=512, lr=2e-4),
}


def get(model_id: str) -> HParams:
    return _HPARAMS.get(model_id, HParams())


def get_dict(model_id: str) -> dict:
    h = get(model_id)
    return {k: v for k, v in h.__dict__.items()}
