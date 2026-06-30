"""
AF-07: Merge del adapter QLoRA → nuevo modelo Ollama (Modelfile).

Una vez entrenado el adapter en RunPod/local, este módulo:
1. Fusiona el adapter con el modelo base (PEFT merge_and_unload)
2. Guarda el modelo fusionado en la SD
3. Genera el Modelfile de Ollama con el system prompt del agente
4. Registra el nuevo modelo en Ollama (ollama create)
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def merge_adapter(
    model_id: str,
    adapter_path: str | Path,
    base_model_name: str,
    output_dir: str | Path | None = None,
    system_prompt: str = "",
) -> dict:
    """
    AF-07: Fusiona el adapter QLoRA con el modelo base.

    Args:
        model_id: ID del modelo (ej: 'cyberagent-24b')
        adapter_path: directorio del adapter PEFT entrenado
        base_model_name: nombre en HuggingFace Hub (ej: 'Qwen/Qwen2.5-24B-Instruct')
        output_dir: dónde guardar el modelo fusionado (None = SD/merged)
        system_prompt: system prompt del agente para el Modelfile

    Returns:
        dict con 'ok', 'merged_path', 'modelfile_path'
    """
    adapter_path = Path(adapter_path)
    if output_dir is None:
        from app.storage.layout import layout
        output_dir = layout.merged_model_path(model_id, adapter_path.name)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fusionar con PEFT
    merge_result = _run_peft_merge(base_model_name, str(adapter_path), str(output_dir))
    if not merge_result["ok"]:
        return merge_result

    # 2. Generar Modelfile
    modelfile_path = output_dir / "Modelfile"
    _write_modelfile(modelfile_path, str(output_dir), system_prompt)

    # 3. Registrar en Ollama
    ollama_name = f"{model_id.replace('/', '-')}-finetuned"
    ollama_result = _register_ollama(ollama_name, str(modelfile_path))

    return {
        "ok": True,
        "merged_path": str(output_dir),
        "modelfile_path": str(modelfile_path),
        "ollama_name": ollama_name,
        "ollama_registered": ollama_result["ok"],
    }


def _run_peft_merge(base_model: str, adapter_path: str, output_dir: str) -> dict:
    """Merge via script Python con PEFT."""
    script = f"""
import sys
try:
    from peft import AutoPeftModelForCausalLM
    import torch
    model = AutoPeftModelForCausalLM.from_pretrained(
        "{adapter_path}",
        torch_dtype=torch.float16,
        device_map="auto",
    )
    merged = model.merge_and_unload()
    merged.save_pretrained("{output_dir}")
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("{base_model}")
    tok.save_pretrained("{output_dir}")
    print("ok")
except Exception as e:
    print(f"error: {{e}}", file=sys.stderr)
    sys.exit(1)
"""
    python = os.environ.get("PYTHON_BIN", "python")
    try:
        result = subprocess.run(
            [python, "-c", script],
            capture_output=True, text=True, timeout=3600,
        )
        if result.returncode == 0:
            return {"ok": True}
        return {"ok": False, "error": result.stderr[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _write_modelfile(path: Path, model_dir: str, system_prompt: str):
    sp = system_prompt or "Eres CyberAgent, un asistente de IA avanzado."
    modelfile = f"""FROM {model_dir}

SYSTEM \"{sp}\"

PARAMETER num_ctx 32768
PARAMETER temperature 0.7
PARAMETER top_p 0.9
"""
    path.write_text(modelfile, encoding="utf-8")


def _register_ollama(name: str, modelfile_path: str) -> dict:
    """Registra el modelo fusionado en Ollama local."""
    try:
        result = subprocess.run(
            ["ollama", "create", name, "-f", modelfile_path],
            capture_output=True, text=True, timeout=600,
        )
        return {"ok": result.returncode == 0, "output": result.stdout[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
