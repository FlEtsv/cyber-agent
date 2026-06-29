#!/usr/bin/env python3
"""
Mistral Usage Monitor - CyberAgent Native

Registra el consumo de tokens en Mistral Studio y calcula el coste acumulado.
Guarda los datos en un CSV y genera resúmenes.
"""

import csv
import os
from datetime import datetime
from typing import Dict, List, Optional

# Tarifas de Mistral Large 3 (junio 2026)
PRICING = {
    "input": 0.80 / 1_000_000,  # $0.80 por millón de tokens
    "output": 2.40 / 1_000_000,  # $2.40 por millón de tokens
}

# Ruta del CSV de logs
LOG_FILE = os.path.join(os.path.dirname(__file__), "mistral_usage_log.csv")


def init_log() -> None:
    """Inicializa el CSV con encabezados si no existe."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "input_tokens", "output_tokens", 
                "cost_input_usd", "cost_output_usd", "total_cost_usd", 
                "context"
            ])


def log_usage(
    input_tokens: int,
    output_tokens: int,
    context: str = "mistral_studio"
) -> None:
    """
    Registra una interacción con Mistral Studio en el CSV.
    Args:
        input_tokens: Tokens enviados a Mistral.
        output_tokens: Tokens recibidos de Mistral.
        context: Contexto de la llamada (ej: "web_search", "code_interpreter").
    """
    init_log()
    cost_input = input_tokens * PRICING["input"]
    cost_output = output_tokens * PRICING["output"]
    total_cost = cost_input + cost_output
    
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            input_tokens,
            output_tokens,
            f"{cost_input:.8f}",
            f"{cost_output:.8f}",
            f"{total_cost:.8f}",
            context
        ])


def get_summary() -> Dict[str, float]:
    """
    Calcula el resumen de consumo acumulado.
    Returns:
        Dict con:
        - total_input_tokens
        - total_output_tokens
        - total_cost_usd
        - avg_cost_per_message
    """
    if not os.path.exists(LOG_FILE):
        return {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_cost_per_message": 0.0,
            "message_count": 0
        }
    
    total_input = 0
    total_output = 0
    total_cost = 0.0
    message_count = 0
    
    with open(LOG_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_input += int(row["input_tokens"])
            total_output += int(row["output_tokens"])
            total_cost += float(row["total_cost_usd"])
            message_count += 1
    
    avg_cost = total_cost / message_count if message_count > 0 else 0.0
    
    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": total_cost,
        "avg_cost_per_message": avg_cost,
        "message_count": message_count
    }


def generate_report() -> str:
    """Genera un informe legible del consumo."""
    summary = get_summary()
    report = (
        f"📊 **Informe de Consumo - Mistral Studio**\n"
        f"- **Mensajes registrados:** {summary['message_count']}\n"
        f"- **Tokens de entrada:** {summary['total_input_tokens']} (~${summary['total_input_tokens'] * PRICING['input']:.6f} USD)\n"
        f"- **Tokens de salida:** {summary['total_output_tokens']} (~${summary['total_output_tokens'] * PRICING['output']:.6f} USD)\n"
        f"- **Coste total:** ${summary['total_cost_usd']:.6f} USD\n"
        f"- **Coste medio por mensaje:** ${summary['avg_cost_per_message']:.6f} USD\n"
        f"- **Coste por 1k tokens (entrada):** ${PRICING['input'] * 1000:.6f} USD\n"
        f"- **Coste por 1k tokens (salida):** ${PRICING['output'] * 1000:.6f} USD\n"
    )
    return report


if __name__ == "__main__":
    # Ejemplo de uso
    print(generate_report())