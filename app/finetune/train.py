"""
Fine-tuning QLoRA con unsloth.
Uso:  py app/finetune/train.py --jsonl data/finetune_xxx.jsonl [opciones]

Dependencias (instalar una vez):
    pip install unsloth trl peft accelerate datasets bitsandbytes
"""
import argparse, json, os, sys


REQUIRED = ["unsloth", "trl", "peft", "accelerate", "datasets"]

DEFAULT_MODEL = "unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit"


def check_deps() -> list[str]:
    missing = []
    for pkg in REQUIRED:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def train(jsonl_path: str, output_dir: str, model_name: str = DEFAULT_MODEL,
          epochs: int = 1, batch_size: int = 2, lr: float = 2e-4,
          max_seq: int = 2048):

    missing = check_deps()
    if missing:
        print(f"[ERROR] Faltan dependencias: {', '.join(missing)}")
        print(f"Instala con: pip install {' '.join(missing)}")
        sys.exit(1)

    from unsloth import FastLanguageModel
    from trl import SFTTrainer, SFTConfig
    from datasets import Dataset

    print(f"[train] Cargando modelo: {model_name}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq,
        dtype=None,
        load_in_4bit=True,
    )

    print("[train] Aplicando adaptadores LoRA...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    print(f"[train] Cargando dataset: {jsonl_path}")
    data = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))

    if not data:
        print("[ERROR] El archivo JSONL está vacío")
        sys.exit(1)

    print(f"[train] {len(data)} pares de conversación encontrados")

    def fmt(example):
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}

    dataset = Dataset.from_list(data).map(fmt)

    os.makedirs(output_dir, exist_ok=True)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=max_seq,
            per_device_train_batch_size=batch_size,
            num_train_epochs=epochs,
            learning_rate=lr,
            output_dir=output_dir,
            logging_steps=1,
            save_strategy="epoch",
            fp16=True,
            report_to="none",
        ),
    )

    print("[train] Iniciando entrenamiento...")
    trainer.train()

    print("[train] Guardando modelo en formato GGUF Q4_K_M...")
    gguf_path = os.path.join(output_dir, "model-cyberagent")
    model.save_pretrained_gguf(gguf_path, tokenizer, quantization_method="q4_k_m")

    modelfile_path = os.path.join(output_dir, "Modelfile")
    with open(modelfile_path, "w") as mf:
        mf.write(f'FROM {gguf_path}-unsloth.Q4_K_M.gguf\n')
        mf.write('PARAMETER temperature 0.6\n')
        mf.write('PARAMETER top_p 0.9\n')
        mf.write('PARAMETER num_ctx 8192\n')

    print(f"[train] Modelo guardado en: {gguf_path}")
    print(f"[train] Para importar a Ollama:")
    print(f"  ollama create cyber-agent-ft -f {modelfile_path}")
    print("[train] COMPLETADO")
    return gguf_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tuning QLoRA para CyberAgent")
    parser.add_argument("--jsonl",       required=True,        help="Ruta al archivo JSONL de entrenamiento")
    parser.add_argument("--output",      default="data/ft_out", help="Directorio de salida")
    parser.add_argument("--model",       default=DEFAULT_MODEL, help="Modelo base HuggingFace")
    parser.add_argument("--epochs",      type=int,   default=1,    help="Épocas de entrenamiento")
    parser.add_argument("--batch-size",  type=int,   default=2,    help="Batch size")
    parser.add_argument("--lr",          type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--max-seq",     type=int,   default=2048, help="Max sequence length")
    args = parser.parse_args()

    train(
        jsonl_path  = args.jsonl,
        output_dir  = args.output,
        model_name  = args.model,
        epochs      = args.epochs,
        batch_size  = args.batch_size,
        lr          = args.lr,
        max_seq     = args.max_seq,
    )
