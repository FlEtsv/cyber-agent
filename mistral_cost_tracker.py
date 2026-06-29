#!/usr/bin/env python3
"""
Mistral Studio Cost Tracker
--------------------------
Registra el coste de cada mensaje en una conversación con Mistral Large 3.
Guarda los datos en un CSV y genera un resumen en tiempo real.

Tarifas (junio 2026):
- Entrada: $0.80 por millón de tokens ($0.0008 por 1k tokens).
- Salida: $2.40 por millón de tokens ($0.0024 por 1k tokens).
"""

import csv
import os
from datetime import datetime
from typing import List, Dict

# Configuración
CSV_PATH = "C:\\Users\\steve\\cyber-llm\\agent-native\\mistral_cost_tracker.csv"
COST_PER_1K_INPUT_TOKENS = 0.0008  # $0.80 por millón → $0.0008 por 1k
COST_PER_1K_OUTPUT_TOKENS = 0.0024  # $2.40 por millón → $0.0024 por 1k


def init_csv() -> None:
    """Crea el CSV con encabezados si no existe."""
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "input_tokens",
                "output_tokens",
                "cost_input_usd",
                "cost_output_usd",
                "total_cost_usd"
            ])


def log_message(input_tokens: int, output_tokens: int) -> None:
    """Registra un mensaje en el CSV."""
    timestamp = datetime.now().isoformat()
    cost_input = (input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS
    cost_output = (output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS
    total_cost = cost_input + cost_output

    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            timestamp,
            input_tokens,
            output_tokens,
            f"{cost_input:.6f}",
            f"{cost_output:.6f}",
            f"{total_cost:.6f}"
        ])


def get_summary() -> Dict[str, float]:
    """Calcula el resumen de costes desde el CSV."""
    if not os.path.exists(CSV_PATH):
        return {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_cost_per_message_usd": 0.0,
            "message_count": 0
        }

    total_input = 0
    total_output = 0
    total_cost = 0.0
    message_count = 0

    with open(CSV_PATH, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            total_input += int(row["input_tokens"])
            total_output += int(row["output_tokens"])
            total_cost += float(row["total_cost_usd"])
            message_count += 1

    avg_cost = total_cost / message_count if message_count > 0 else 0.0
    avg_cost_per_token = (total_cost / (total_input + total_output)) * 1000 if (total_input + total_output) > 0 else 0.0

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": total_cost,
        "avg_cost_per_message_usd": avg_cost,
        "avg_cost_per_1k_tokens_usd": avg_cost_per_token,
        "message_count": message_count
    }


def generate_report(summary: Dict[str, float]) -> str:
    """Genera un informe legible en texto."""
    report = (
        "=== Resumen de Costes en Mistral Studio ===\n"
        f"Mensajes registrados: {summary['message_count']}\n"
        f"Tokens de entrada: {summary['total_input_tokens']} "
        f"(${summary['total_input_tokens'] / 1000 * COST_PER_1K_INPUT_TOKENS:.6f} USD)\n"
        f"Tokens de salida: {summary['total_output_tokens']} "
        f"(${summary['total_output_tokens'] / 1000 * COST_PER_1K_OUTPUT_TOKENS:.6f} USD)\n"
        f"Coste total: ${summary['total_cost_usd']:.6f} USD\n"
        f"Coste medio por mensaje: ${summary['avg_cost_per_message_usd']:.6f} USD\n"
        f"Coste medio por 1k tokens: ${summary['avg_cost_per_1k_tokens_usd']:.6f} USD\n"
        "\n=== Detalle de tarifas ===\n"
        f"Entrada: ${COST_PER_1K_INPUT_TOKENS * 1000} USD por millón de tokens\n"
        f"Salida: ${COST_PER_1K_OUTPUT_TOKENS * 1000} USD por millón de tokens\n"
        f"CSV guardado en: {CSV_PATH}"
    )
    return report


if __name__ == "__main__":
    # Inicializa el CSV
    init_csv()
    
    # Registra los mensajes de esta conversación (estimaciones)
    messages = [
        {"input_tokens": 50, "output_tokens": 200},   # Tu primer mensaje + mi respuesta
        {"input_tokens": 30, "output_tokens": 400},   # Segundo intercambio
        {"input_tokens": 40, "output_tokens": 0},     # Tu tercer mensaje (solo entrada)
        {"input_tokens": 100, "output_tokens": 300},  # Este intercambio
    ]
    
    for msg in messages:
        log_message(msg["input_tokens"], msg["output_tokens"])
    
    # Genera el resumen
    summary = get_summary()
    report = generate_report(summary)
    print(report)