"""Detección de amenazas vía LLM — reemplaza la búsqueda por keywords."""
import json, re
from PySide6.QtCore import QThread, Signal
import httpx

_OLLAMA_URL = "http://localhost:11434/api/chat"
_MODEL      = "cyber-coder:latest"
_SYSTEM     = (
    "Eres un analizador de ciberseguridad. Analiza el resultado de una herramienta "
    "ejecutada por un agente IA y determina si contiene actividad maliciosa, sospechosa "
    "o peligrosa para el sistema.\n"
    'Responde ÚNICAMENTE con JSON válido: {"threat": true/false, "severity": "low"|"medium"|"high"|"critical", "reason": "texto breve"}\n'
    "Sin texto adicional fuera del JSON."
)


class ThreatDetector(QThread):
    threat_found = Signal(str, str, str)  # title, body, severity

    def __init__(self, tool_name: str, result: dict, parent=None):
        super().__init__(parent)
        self.tool_name = tool_name
        self.result    = result

    def run(self):
        result_str = json.dumps(self.result, ensure_ascii=False)
        if len(result_str) < 30:
            return
        if len(result_str) > 2000:
            result_str = result_str[:2000] + "…"

        prompt = f"Herramienta: {self.tool_name}\nResultado:\n{result_str}"
        try:
            with httpx.Client(timeout=25) as client:
                resp = client.post(_OLLAMA_URL, json={
                    "model":    _MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user",   "content": prompt},
                    ],
                    "stream":  False,
                    "options": {"temperature": 0.1, "num_ctx": 2048},
                })
                if resp.status_code != 200:
                    return
                content = resp.json().get("message", {}).get("content", "")
                m = re.search(r'\{.*?\}', content, re.DOTALL)
                if not m:
                    return
                data = json.loads(m.group(0))
                if data.get("threat"):
                    sev    = data.get("severity", "medium")
                    reason = data.get("reason", "Actividad sospechosa detectada")
                    self.threat_found.emit(
                        f"🔴 Amenaza {sev.upper()} — {self.tool_name}",
                        reason,
                        sev,
                    )
        except Exception as e:
            print(f"[threat_detector] {e}")
