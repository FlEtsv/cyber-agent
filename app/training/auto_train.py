"""
X-01..X-11: Auto-entrenamiento — pipeline automático QLoRA.

Flujo completo:
  X-01: Cola de entrenamiento (una job a la vez por modelo)
  X-02: Trigger automático (N muestras nuevas o tiempo transcurrido)
  X-03: Construcción del dataset desde training_store
  X-04: Detección de presencia del usuario (no entrenar si está usando el PC)
  X-05: Lanzar entrenamiento (local GPU o RunPod)
  X-06: Monitorizar progreso
  X-07: Evaluar adapter nuevo (evaluate.py)
  X-08: Comparación A/B contra baseline
  X-09: Promover o rechazar el nuevo adapter
  X-10: Merge y registro en Ollama (merge.py)
  X-11: Rollback si falla evaluación

Estado persistido en data/training_queue.json.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

_STATE_PATH = Path("data/training_queue.json")
_lock = threading.Lock()

TrainingStatus = Literal["pending", "building", "training", "evaluating", "promoting", "done", "failed", "skipped"]


@dataclass
class TrainingJob:
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    model_id: str = "cyberagent-24b"
    status: TrainingStatus = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0
    n_samples: int = 0
    adapter_version: str = ""
    eval_score: float = 0.0
    baseline_score: float = 0.0
    promoted: bool = False
    error: str = ""
    trigger: str = "manual"   # manual | samples | schedule


# ── X-01: Cola ────────────────────────────────────────────────────────────────

def _load_queue() -> list[dict]:
    if _STATE_PATH.exists():
        try:
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_queue(jobs: list[dict]) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue(model_id: str = "cyberagent-24b", trigger: str = "manual") -> TrainingJob:
    """X-01: Añade un job a la cola."""
    job = TrainingJob(model_id=model_id, trigger=trigger)
    with _lock:
        jobs = _load_queue()
        # No encolar si ya hay un job pending/training para el mismo modelo
        for j in jobs:
            if j.get("model_id") == model_id and j.get("status") in ("pending", "training"):
                logger.info("auto_train: ya hay un job activo para %s", model_id)
                return TrainingJob(**j)
        jobs.append(asdict(job))
        _save_queue(jobs)
    logger.info("auto_train: job %s encolado para %s (trigger=%s)", job.job_id, model_id, trigger)
    return job


def cancel(job_id: str) -> bool:
    with _lock:
        jobs = _load_queue()
        for j in jobs:
            if j["job_id"] == job_id and j["status"] in ("pending",):
                j["status"] = "skipped"
                _save_queue(jobs)
                return True
    return False


def list_jobs() -> list[dict]:
    return _load_queue()


def get_job(job_id: str) -> dict | None:
    for j in _load_queue():
        if j["job_id"] == job_id:
            return j
    return None


def _update_job(job_id: str, **kwargs) -> None:
    with _lock:
        jobs = _load_queue()
        for j in jobs:
            if j["job_id"] == job_id:
                j.update(kwargs)
        _save_queue(jobs)


# ── X-02: Trigger automático ──────────────────────────────────────────────────

# Umbrales configurables
SAMPLES_THRESHOLD = int(os.environ.get("TRAINING_SAMPLES_THRESHOLD", "200"))
SCHEDULE_INTERVAL_HOURS = float(os.environ.get("TRAINING_SCHEDULE_HOURS", "24"))

_last_triggered: dict[str, float] = {}


def check_and_trigger(model_id: str = "cyberagent-24b") -> bool:
    """
    X-02: Verifica si se debe disparar entrenamiento automático.

    Condiciones:
    - Hay >= SAMPLES_THRESHOLD muestras nuevas
    - O ha pasado SCHEDULE_INTERVAL_HOURS desde el último entrenamiento
    """
    # Check user presence (X-04)
    if not _can_train():
        return False

    # Check muestras
    try:
        from app.training_store import count as ts_count
        new_samples = ts_count()
        if new_samples >= SAMPLES_THRESHOLD:
            logger.info("auto_train: %d muestras → disparando entrenamiento", new_samples)
            enqueue(model_id, trigger="samples")
            return True
    except Exception:
        pass

    # Check schedule
    last = _last_triggered.get(model_id, 0)
    if time.time() - last > SCHEDULE_INTERVAL_HOURS * 3600:
        logger.info("auto_train: schedule trigger para %s", model_id)
        enqueue(model_id, trigger="schedule")
        _last_triggered[model_id] = time.time()
        return True

    return False


# ── X-04: Detección de presencia ──────────────────────────────────────────────

def _can_train() -> bool:
    """X-04: ¿Puede entrenar ahora? No si el usuario está activo."""
    try:
        from app.training.scheduler import can_train
        ok, _ = can_train()
        return ok
    except Exception:
        return True


# ── X-03: Construcción del dataset ───────────────────────────────────────────

def _build_dataset(model_id: str, job_id: str) -> tuple[list[dict], str]:
    """X-03: Construye el dataset desde training_store."""
    import tempfile
    from app.training_store import export as ts_export
    version = time.strftime("v%Y%m%d_%H%M%S")

    # Exportar a JSONL temporal
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        tmp_path = tf.name
    export_path = ts_export(path=tmp_path, min_signal=0.0)

    # Leer muestras
    samples: list[dict] = []
    try:
        with open(export_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
    except Exception:
        pass

    # Guardar en SD
    from app.storage.datasets import save_dataset
    save_dataset(model_id, samples, version=version, metadata={"job_id": job_id, "trigger": "auto"})

    logger.info("auto_train: dataset %s construido (%d muestras)", version, len(samples))
    return samples, version


# ── X-05..X-11: Pipeline completo ────────────────────────────────────────────

def run_pipeline(job_id: str) -> dict:
    """
    X-05..X-11: Ejecuta el pipeline completo para un job.
    Llamado en background desde el worker thread.
    """
    job = get_job(job_id)
    if not job:
        return {"ok": False, "error": "job no encontrado"}

    model_id = job["model_id"]
    _update_job(job_id, status="building", started_at=time.time())

    try:
        # X-03: Dataset
        samples, version = _build_dataset(model_id, job_id)
        _update_job(job_id, n_samples=len(samples), adapter_version=version)

        if len(samples) < 10:
            _update_job(job_id, status="skipped", error="Menos de 10 muestras")
            return {"ok": False, "reason": "too_few_samples"}

        # X-05: Entrenamiento (stub — RunPod o local)
        _update_job(job_id, status="training")
        adapter_path = _launch_training(model_id, version, samples)
        if not adapter_path:
            _update_job(job_id, status="failed", error="Entrenamiento fallido")
            return {"ok": False, "reason": "training_failed"}

        # X-07: Evaluación
        _update_job(job_id, status="evaluating")
        from app.training.evaluate import evaluate, should_promote
        result = evaluate(model_id, version, _split_eval(samples))
        baseline = _get_baseline_score(model_id)
        _update_job(job_id, eval_score=result.final_score, baseline_score=baseline)

        # X-08+X-09: Comparación A/B y decisión de promover
        if should_promote(result, baseline):
            _update_job(job_id, status="promoting")
            # X-10: Merge y registro en Ollama
            from app.training.merge import merge_adapter
            merge_result = merge_adapter(model_id, adapter_path, _base_model(model_id))
            promoted = merge_result.get("ok", False)
            _update_job(job_id, promoted=promoted)
            if promoted:
                _set_baseline_score(model_id, result.final_score)
                _mark_samples_used(model_id)
                logger.info("auto_train: adapter %s promovido (%.3f > %.3f)", version, result.final_score, baseline)
        else:
            logger.info("auto_train: adapter %s rechazado (%.3f <= %.3f)", version, result.final_score, baseline)
            # X-11: No promover — rollback implícito (no hacemos nada)

        _update_job(job_id, status="done", finished_at=time.time())
        return {"ok": True, "job_id": job_id, "promoted": job.get("promoted", False)}

    except Exception as e:
        logger.error("auto_train.run_pipeline: %s", e)
        _update_job(job_id, status="failed", error=str(e), finished_at=time.time())
        return {"ok": False, "error": str(e)}


def _launch_training(model_id: str, version: str, samples: list[dict]) -> str | None:
    """X-05: Stub — en producción llama a RunPod o GPU local."""
    from app.storage.layout import layout
    adapter_path = layout.adapter_path(model_id, version)
    adapter_path.mkdir(parents=True, exist_ok=True)
    # Stub: simula adapter creado (en prod: huggingface/trl QLoRA)
    (adapter_path / "adapter_config.json").write_text(
        json.dumps({"base_model_name": _base_model(model_id), "version": version}),
        encoding="utf-8",
    )
    return str(adapter_path)


def _split_eval(samples: list[dict]) -> list[dict]:
    """70/30 split — retorna el 30% de evaluación."""
    split = int(len(samples) * 0.7)
    return samples[split:]


def _base_model(model_id: str) -> str:
    base_models = {
        "cyberagent-24b": "Qwen/Qwen2.5-24B-Instruct",
        "codestral": "mistralai/Codestral-22B-v0.1",
    }
    return base_models.get(model_id, model_id)


_baseline_scores: dict[str, float] = {}


def _get_baseline_score(model_id: str) -> float:
    return _baseline_scores.get(model_id, 0.5)


def _set_baseline_score(model_id: str, score: float) -> None:
    _baseline_scores[model_id] = score


def _mark_samples_used(model_id: str) -> None:
    try:
        from app.training_store import mark_used
        import sqlite3
        from pathlib import Path
        db = Path("data/training_store.db")
        if db.exists():
            with sqlite3.connect(str(db)) as c:
                ids = [r[0] for r in c.execute("SELECT id FROM samples").fetchall()]
            if ids:
                mark_used(ids)
    except Exception:
        pass


# ── Worker thread ─────────────────────────────────────────────────────────────

_worker_running = False


def _worker_loop() -> None:
    while _worker_running:
        jobs = _load_queue()
        pending = [j for j in jobs if j.get("status") == "pending"]
        if pending and _can_train():
            job = pending[0]
            run_pipeline(job["job_id"])
        time.sleep(60)


def start_worker() -> None:
    global _worker_running
    if _worker_running:
        return
    _worker_running = True
    threading.Thread(target=_worker_loop, name="AutoTrainWorker", daemon=True).start()
    logger.info("auto_train: worker iniciado")


def stop_worker() -> None:
    global _worker_running
    _worker_running = False


def status() -> dict:
    jobs = _load_queue()
    return {
        "worker_running": _worker_running,
        "pending": len([j for j in jobs if j.get("status") == "pending"]),
        "training": len([j for j in jobs if j.get("status") == "training"]),
        "done": len([j for j in jobs if j.get("status") == "done"]),
        "failed": len([j for j in jobs if j.get("status") == "failed"]),
        "samples_threshold": SAMPLES_THRESHOLD,
    }
