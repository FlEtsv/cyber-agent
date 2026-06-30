# RunPod QLoRA Training Pipeline

> K-06: Guía de entrenamiento QLoRA en RunPod A100.
> Para modelos que no caben en local (>16 GB VRAM) o cuando se requiere A100.

## Requisitos

- **RUNPOD_API_KEY** en el vault (`app.secrets_vault.get_secret("RUNPOD_API_KEY")`)
- Dataset exportado con `app.training.dataset_builder.export_jsonl()`
- Modelo base en Hugging Face Hub (o quantizado local)

## Flujo automático (vía orquestador)

```
app.training.orchestrator.start_training(model_id)
  → preflight.run() — verifica VRAM/disco/usuario
  → dataset_builder.build() — filtra + dedup + split
  → runner_runpod.run() — sube dataset, lanza pod A100, descarga adapter
  → versioning.register_version() — guarda adapter
  → comms.router.notify_agent_done() — notifica
```

## Lanzamiento manual

```python
from app.training.runner_runpod import RunPodRunner

runner = RunPodRunner(
    model_id="cyberagent-24b",
    dataset_path="data/training_export.jsonl",
    output_dir="models/adapters/cyberagent-24b-v2",
)
runner.run()
```

## Hiperparámetros QLoRA por modelo

| Modelo | Base | VRAM (train) | Horas A100 | Coste $ |
|--------|------|--------------|------------|---------|
| cyberagent-24b | Qwen2.5-24B-Instruct | ~40 GB | ~4h | ~$3.5 |
| codestral | Codestral-22B | ~35 GB | ~3h | ~$2.5 |
| vision-security | LLaVA-13B | ~26 GB | ~2h | ~$1.5 |
| tool-router | Phi-3-mini-3.8B | ~8 GB | ~0.5h | ~$0.4 |

Todos usan: `rank=16, alpha=32, lr=2e-4, epochs=3, batch=4` (defaults en `app/training/hparams.py`).

## Merge del adapter → Ollama (AF-07)

Una vez entrenado, fusionar el adapter con el modelo base:

```bash
# Merge con llm-adapters o PEFT
python -c "
from peft import PeftModel, AutoPeftModelForCausalLM
import torch

model = AutoPeftModelForCausalLM.from_pretrained(
    'models/adapters/cyberagent-24b-v2',
    torch_dtype=torch.float16,
)
merged = model.merge_and_unload()
merged.save_pretrained('models/merged/cyberagent-24b-v2')
"

# Crear Modelfile para Ollama
cat > Modelfile <<EOF
FROM models/merged/cyberagent-24b-v2
SYSTEM "Eres CyberAgent..."
PARAMETER num_ctx 32768
EOF

ollama create cyberagent-24b-v2 -f Modelfile
```

## Rollback

```python
from app.training.versioning import rollback
rollback("cyberagent-24b")  # vuelve al adapter anterior
```

## Variables de entorno necesarias

```env
RUNPOD_API_KEY=rp_xxx   # en vault como SEC_RUNPOD_API_KEY
HF_TOKEN=hf_xxx          # para descargar base model
```
