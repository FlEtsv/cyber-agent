"""
Mantiene el modelo de Ollama cargado en VRAM enviando un ping cada N minutos.
Sin esto, Ollama descarga el modelo tras 5 min de inactividad y la primera
respuesta tras ese periodo tarda 20-30 segundos en recargar.
"""
import threading, time, httpx, json

_stop = threading.Event()
_PING_INTERVAL = 240   # 4 minutos (Ollama descarga tras 5 min por defecto)
_OLLAMA_URL    = "http://localhost:11434/api/chat"


def _ping(model: str):
    try:
        payload = {
            "model":   model,
            "messages": [{"role": "user", "content": "ok"}],
            "stream":  False,
            "options": {"num_predict": 1, "num_ctx": 512},
        }
        with httpx.Client(timeout=30) as client:
            client.post(_OLLAMA_URL, json=payload)
    except Exception:
        pass   # si falla, no pasa nada — lo intentará de nuevo


def _loop(model: str, interval: int):
    while not _stop.wait(interval):
        _ping(model)


def start_keepalive(model: str, interval: int = _PING_INTERVAL):
    t = threading.Thread(target=_loop, args=(model, interval),
                         daemon=True, name="OllamaKeepalive")
    t.start()
    print(f"[keepalive] Modelo '{model}' activo en VRAM — ping cada {interval//60} min")


def stop_keepalive():
    _stop.set()
