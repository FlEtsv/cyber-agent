"""
AF-01 + AF-05 + AF-06 + AF-08: Orquestador de entrenamiento.

Flujo:
  1. preflight (AF-02)
  2. preparar dataset (AC) + sanitizar (AC-06)
  3. decidir local vs RunPod (AF-05)
  4. lanzar runner (AF-03 / AF-04)
  5. stream de progreso → SSE (AF-06)
  6. evaluar (AG-01+AG-02)
  7. promover o rollback (AG-03)
  8. notificar (AG-07)
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Generator


class TrainingOrchestrator:
    """
    Gestiona un run de entrenamiento completo.
    Emite eventos de progreso via .events() (generador).
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._run_id: int | None = None

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        """AF-08: cancelar entrenamiento en curso."""
        self._stop.set()

    def events(self) -> Generator[dict, None, None]:
        """SSE-style events: {type, data}."""
        while True:
            try:
                evt = self._q.get(timeout=2.0)
                yield evt
                if evt["type"] in ("done", "error", "cancelled"):
                    break
            except queue.Empty:
                if self._stop.is_set():
                    yield {"type": "cancelled", "data": "Entrenamiento cancelado"}
                    break

    def _emit(self, type_: str, data) -> None:
        self._q.put({"type": type_, "data": data})

    def _run(self) -> None:
        try:
            self._emit("status", "🔍 Ejecutando preflight…")

            # AF-02: preflight
            from app.training.preflight import run as preflight
            pf = preflight(self.model_id)
            self._emit("preflight", pf)
            if not pf["ok"]:
                self._emit("error", f"Preflight fallido: {'; '.join(pf['errors'])}")
                return

            # Preparar dataset
            self._emit("status", "📦 Preparando dataset…")
            from app.training.dataset_builder import build, export_jsonl
            from app.training.sanitize import sanitize_samples
            from app.training.registry import get as get_card
            from app.training.hparams import get_dict as get_hparams
            from app.training.audit import record_run, update_run

            ds = build(self.model_id)
            train_samples = sanitize_samples(ds["train"])
            eval_samples = sanitize_samples(ds["eval"])
            self._emit("dataset", ds["stats"])

            card = get_card(self.model_id)
            hparams = get_hparams(self.model_id)

            # Registrar en auditoría
            self._run_id = record_run(
                self.model_id,
                n_samples=ds["stats"]["total"],
                destination=card.destination if card else "local",
                hparams=hparams,
            )
            update_run(self._run_id, "running")

            # Export a JSONL
            out_dir = Path(__file__).parent.parent.parent / "data" / "training_runs" / self.model_id
            out_dir.mkdir(parents=True, exist_ok=True)
            train_path = export_jsonl(train_samples, out_dir / "train.jsonl")
            eval_path = export_jsonl(eval_samples, out_dir / "eval.jsonl")
            self._emit("status", f"💾 Dataset guardado: {len(train_samples)} train + {len(eval_samples)} eval")

            if self._stop.is_set():
                update_run(self._run_id, "failed", notes="Cancelado por el usuario")
                self._emit("cancelled", "Cancelado")
                return

            # AF-05: decidir runner
            destination = card.destination if card else "local"
            self._emit("status", f"🚀 Iniciando entrenamiento ({destination})…")

            if destination == "runpod":
                from app.training.runner_runpod import run as run_runpod
                result = run_runpod(self.model_id, train_path, eval_path, hparams,
                                    progress_cb=lambda p: self._emit("progress", p))
            else:
                from app.training.runner_local import run as run_local
                result = run_local(self.model_id, train_path, eval_path, hparams,
                                   progress_cb=lambda p: self._emit("progress", p),
                                   stop_flag=self._stop)

            if not result.get("ok"):
                update_run(self._run_id, "failed", notes=result.get("error", ""))
                self._emit("error", f"Entrenamiento fallido: {result.get('error', '')}")
                return

            # AG-01..AG-02: evaluación
            metrics = result.get("metrics", {})
            self._emit("metrics", metrics)

            # AG-07: notificar resultado
            self._emit("status", "📢 Notificando resultado…")
            _notify_result(self.model_id, metrics)

            update_run(self._run_id, "done", metrics=metrics)
            self._emit("done", {"model_id": self.model_id, "metrics": metrics, "run_id": self._run_id})

        except Exception as exc:
            import traceback
            err = str(exc) + "\n" + traceback.format_exc()
            if self._run_id:
                try:
                    from app.training.audit import update_run
                    update_run(self._run_id, "failed", notes=str(exc))
                except Exception:
                    pass
            self._emit("error", err)


def _notify_result(model_id: str, metrics: dict) -> None:
    try:
        from app.comms.router import send_message, SUCCESS, ERROR
        loss = metrics.get("eval_loss")
        promoted = metrics.get("promoted", False)
        msg = f"Modelo: {model_id}"
        if loss is not None:
            msg += f"\nEval loss: {loss:.4f}"
        if promoted:
            msg += "\n✅ Promovido a producción"
        send_message(
            title="🏋️ Entrenamiento completado",
            body=msg,
            level=SUCCESS if promoted else ERROR,
        )
    except Exception:
        pass


# ── Registro de runs en curso ──────────────────────────────────────────────────

_active_runs: dict[str, TrainingOrchestrator] = {}
_runs_lock = threading.Lock()


def start_training(model_id: str) -> dict:
    with _runs_lock:
        if model_id in _active_runs:
            return {"ok": False, "error": f"Ya hay un run activo para {model_id}"}
        orch = TrainingOrchestrator(model_id)
        _active_runs[model_id] = orch
    orch.start()
    return {"ok": True, "model_id": model_id, "message": "Entrenamiento iniciado"}


def cancel_training(model_id: str) -> dict:
    with _runs_lock:
        orch = _active_runs.pop(model_id, None)
    if not orch:
        return {"ok": False, "error": "Sin run activo para ese modelo"}
    orch.stop()
    return {"ok": True, "model_id": model_id}


def active_runs() -> list[str]:
    with _runs_lock:
        return list(_active_runs.keys())
