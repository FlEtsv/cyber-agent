"""
Cerebro multi-backend del agente.

Permite que el bucle del agente (desktop y API) hable indistintamente con:
  - Ollama local  (modelos `cyberagent-*`, `qwen*`, etc.)
  - Mistral cloud (mistral-large-latest, mistral-medium-latest, magistral-*)

Y un modo FUSED donde Mistral dirige pero puede delegar en el modelo local
(privacidad / sin conexión / coste) y viceversa.

El objetivo es que `_stream_once` no tenga que saber con qué backend habla:
llama a `stream_brain(...)` y recibe `(content, tool_calls, reasoning)` con la
misma forma que ya producía el camino de Ollama.
"""
from __future__ import annotations

import json
import os
import re
import string
from typing import Any, Callable

import httpx

# ── Identidad de modelos ─────────────────────────────────────────────────────
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").rstrip("/")

# Modelos que enrutamos al backend Mistral. `magistral-*` son los de razonamiento.
MISTRAL_MODELS = {
    "mistral-large-latest",
    "mistral-medium-latest",
    "mistral-small-latest",
    "magistral-medium-latest",
    "magistral-small-latest",
    "pixtral-large-latest",
    "codestral-latest",          # Codestral: cerebro de código (chat + tool-calling)
}

# Alias internos del selector de la UI
FUSED_MODEL = "fused"           # Mistral dirige + delega en local
AUTO_MODEL = "auto"             # el router decide

# Modelos de razonamiento explícito (emiten <think>...</think> o campo reasoning)
_REASONING_MODELS = {"magistral-medium-latest", "magistral-small-latest"}


def mistral_api_key() -> str:
    return (
        os.getenv("MISTRAL_API_KEY")
        or os.getenv("MISTRAL_STUDIO_API_KEY")
        or ""
    ).strip()


def mistral_available() -> bool:
    return bool(mistral_api_key())


def is_mistral_model(model: str | None) -> bool:
    if not model:
        return False
    m = model.strip().lower()
    # Un ":" indica tag de Ollama (modelo LOCAL, p.ej. codestral:22b) → nunca es nube.
    if ":" in m:
        return False
    if m in MISTRAL_MODELS or m == FUSED_MODEL:
        return True
    # OJO: solo "codestral-..." (nube). El local de Ollama es "codestral:22b" y ya
    # se descartó por el ":" de arriba.
    return (m.startswith("mistral-") or m.startswith("magistral-")
            or m.startswith("pixtral-") or m.startswith("codestral-"))


def resolve_model(model: str | None) -> str:
    """Convierte alias del selector (fused) en el id real de Mistral a usar."""
    m = (model or "").strip().lower()
    if m == FUSED_MODEL:
        # RENTABLE: la nube por defecto es Mistral Small 3 (≈$0.10/$0.30, ~6x más
        # barato que Medium). Para razonamiento duro puntual, elige Medium a mano.
        return os.getenv("CYBERAGENT_FUSED_MODEL", "mistral-small-latest")
    if m in ("", AUTO_MODEL):
        return os.getenv("CYBERAGENT_MISTRAL_MODEL", "mistral-small-latest")
    return model


def is_fused(model: str | None) -> bool:
    return (model or "").strip().lower() == FUSED_MODEL


# ── Normalización de historial al formato Mistral ────────────────────────────
_ALNUM = string.ascii_letters + string.digits


def _short_id(seed: str) -> str:
    """Mistral exige tool_call_id de exactamente 9 caracteres alfanuméricos."""
    import hashlib
    h = hashlib.sha1(seed.encode("utf-8", errors="ignore")).hexdigest()
    out = "".join(c for c in h if c in _ALNUM)[:9]
    return (out + "abcdefghi")[:9]


def to_mistral_messages(history: list[dict]) -> list[dict]:
    """
    Adapta nuestro historial (estilo OpenAI/Ollama) al contrato de Mistral:
      - assistant.tool_calls[].function.arguments debe ser STRING JSON.
      - tool_call_id debe ser [A-Za-z0-9]{9}; remapeamos manteniendo coherencia.
      - cada assistant.tool_call DEBE tener su tool response y viceversa
        (si no, Mistral devuelve 400). Saneamos huérfanos tras compactación.
    """
    # Pase 1: ids de assistant-tool_calls y de respuestas tool (por id antiguo)
    call_ids: set[str] = set()
    resp_ids: set[str] = set()
    for msg in history:
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for i, tc in enumerate(msg["tool_calls"]):
                call_ids.add(str(tc.get("id") or f"call_{i}"))
        elif msg.get("role") == "tool":
            resp_ids.add(str(msg.get("tool_call_id") or ""))
    valid = call_ids & resp_ids  # solo pares completos sobreviven

    id_map: dict[str, str] = {}
    out: list[dict] = []
    for msg in history:
        role = msg.get("role")
        if role == "assistant" and msg.get("tool_calls"):
            new_calls = []
            for i, tc in enumerate(msg["tool_calls"]):
                old = str(tc.get("id") or f"call_{i}")
                if old not in valid:
                    continue  # call sin respuesta → se descarta
                new = id_map.get(old) or _short_id(old + str(i) + str(len(out)))
                id_map[old] = new
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, (dict, list)):
                    args = json.dumps(args, ensure_ascii=False)
                elif args is None:
                    args = "{}"
                new_calls.append({
                    "id": new,
                    "type": "function",
                    "function": {"name": fn.get("name", ""), "arguments": args},
                })
            if new_calls:
                out.append({"role": "assistant",
                            "content": msg.get("content") or "",
                            "tool_calls": new_calls})
            elif (msg.get("content") or "").strip():
                out.append({"role": "assistant", "content": msg["content"]})
            # assistant sin calls válidas ni texto → se omite
        elif role == "tool":
            old = str(msg.get("tool_call_id") or "")
            if old not in valid or old not in id_map:
                continue  # respuesta huérfana o sin call previa válida → se descarta
            out.append({
                "role": "tool",
                "tool_call_id": id_map[old],
                "name": msg.get("name", ""),
                "content": msg.get("content") or "",
            })
        else:
            # system / user / assistant-sin-tools
            out.append({"role": role, "content": msg.get("content") or ""})
    return out


def compact_for_mistral(history: list[dict], budget_tokens: int | None = None) -> list[dict]:
    """Compacta el historial antes de mandarlo a Mistral.

    Antes el camino Mistral enviaba el historial completo sin recortar: los
    resultados de herramienta largos lo inflaban y el agente se quedaba sin
    contexto y paraba pronto. Aquí (1) acortamos contenidos largos y (2)
    recortamos los turnos más antiguos hasta un presupuesto de tokens,
    conservando el system y lo más reciente. El emparejamiento tool_call↔tool
    lo repara después `to_mistral_messages` (descarta huérfanos).
    """
    if not history:
        return history
    try:
        from app.ollama_client import _compact_message, _estimate_tokens
    except Exception:
        return history
    if budget_tokens is None:
        budget_tokens = int(os.getenv("CYBERAGENT_MISTRAL_BUDGET_TOKENS", "12000"))

    system = history[0] if history[0].get("role") == "system" else None
    rest = history[1:] if system else history
    sys_c = _compact_message(system) if system else None
    used = _estimate_tokens(sys_c) if sys_c else 0

    selected: list[dict] = []
    for msg in reversed(rest):
        c = _compact_message(msg)
        cost = _estimate_tokens(c)
        if used + cost <= budget_tokens or not selected:
            selected.append(c)
            used += cost
        else:
            break
    selected.reverse()
    return ([sys_c] if sys_c else []) + selected


# ── Streaming Mistral ────────────────────────────────────────────────────────
_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)


def split_think(delta: str, in_think: bool) -> tuple[str, str, bool]:
    """Procesa un trozo de contenido que puede llevar tags <think>...</think>.
    Devuelve (texto_razonamiento, texto_respuesta, nuevo_in_think). Permite separar
    el razonamiento nativo (qwen3/huihui en modo herramientas mete <think> inline)
    para mandarlo al panel de proceso y dejar la respuesta final limpia."""
    reasoning = ""
    out = ""
    buf = delta or ""
    while buf:
        if not in_think:
            i = buf.find("<think>")
            jc = buf.find("</think>")
            # Cierre huérfano (sin apertura): qwen3 con herramientas a veces consume
            # el <think> y deja el razonamiento + </think> colados → lo previo es proceso.
            if jc != -1 and (i == -1 or jc < i):
                reasoning += buf[:jc]
                buf = buf[jc + 8:]
                continue
            if i == -1:
                out += buf
                buf = ""
            else:
                out += buf[:i]
                buf = buf[i + 7:]
                in_think = True
        else:
            j = buf.find("</think>")
            if j == -1:
                reasoning += buf
                buf = ""
            else:
                reasoning += buf[:j]
                buf = buf[j + 8:]
                in_think = False
    return reasoning, out, in_think


def strip_lead_artifacts(text: str) -> str:
    """Quita basura de cabecera: espacios + caracteres CJK sueltos (p.ej. '润色')
    que algunos GGUF abliterados emiten al INICIO de la respuesta en modo
    herramientas. Solo aplicar al primer trozo del contenido."""
    s = (text or "").lstrip()
    i = 0
    while i < len(s) and ("㐀" <= s[i] <= "鿿" or "豈" <= s[i] <= "﫿"):
        i += 1
    return s[i:].lstrip() if i else s


def stream_mistral(
    model: str,
    history: list[dict],
    tools: list | None,
    emit_token: Callable[[str], None],
    emit_reasoning: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    temperature: float = 0.4,
    max_tokens: int = 4096,
) -> tuple[str, dict, str]:
    """
    Devuelve (content, tool_calls, reasoning).
    tool_calls: {idx: {"name": str, "args": str(JSON)}}  (misma forma que Ollama).
    """
    key = mistral_api_key()
    if not key:
        raise RuntimeError(
            "MISTRAL_API_KEY no está configurada. Ponla con:\n"
            '  setx MISTRAL_API_KEY "tu_clave"\n'
            "y reinicia la app (o exporta la variable en el entorno del servicio)."
        )

    real_model = resolve_model(model)
    messages = to_mistral_messages(compact_for_mistral(history))

    payload: dict[str, Any] = {
        "model": real_model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream_options": {"include_usage": True},
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if real_model in _REASONING_MODELS:
        # los magistral exponen el razonamiento; lo dejamos fluir aparte
        payload["temperature"] = max(temperature, 0.7)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=5.0)

    content = ""
    reasoning = ""
    tool_calls: dict[int, dict] = {}
    in_think = False
    usage_info: dict | None = None

    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", f"{MISTRAL_BASE_URL}/chat/completions",
                            json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = resp.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Mistral HTTP {resp.status_code}: {body[:600]}")
            for line in resp.iter_lines():
                if should_stop and should_stop():
                    break
                if not line:
                    continue
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    continue
                _u = chunk.get("usage")
                if _u:
                    usage_info = _u
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {}) or {}

                # razonamiento nativo (magistral) si viene en campo aparte
                rdelta = delta.get("reasoning_content") or delta.get("reasoning")
                if rdelta:
                    reasoning += rdelta
                    if emit_reasoning:
                        emit_reasoning(rdelta)

                piece = delta.get("content")
                if piece:
                    # separar <think>...</think> embebido en el contenido
                    buf = piece
                    while buf:
                        if not in_think:
                            open_i = buf.find("<think>")
                            if open_i == -1:
                                content += buf
                                emit_token(buf)
                                buf = ""
                            else:
                                pre = buf[:open_i]
                                if pre:
                                    content += pre
                                    emit_token(pre)
                                buf = buf[open_i + len("<think>"):]
                                in_think = True
                        else:
                            close_i = buf.find("</think>")
                            if close_i == -1:
                                reasoning += buf
                                if emit_reasoning:
                                    emit_reasoning(buf)
                                buf = ""
                            else:
                                seg = buf[:close_i]
                                reasoning += seg
                                if emit_reasoning and seg:
                                    emit_reasoning(seg)
                                buf = buf[close_i + len("</think>"):]
                                in_think = False

                for tc in delta.get("tool_calls", []) or []:
                    idx = tc.get("index", len(tool_calls))
                    if idx not in tool_calls:
                        tool_calls[idx] = {"name": "", "args": ""}
                    fn = tc.get("function", {}) or {}
                    if fn.get("name"):
                        tool_calls[idx]["name"] = fn["name"]
                    args = fn.get("arguments", "")
                    if isinstance(args, (dict, list)):
                        args = json.dumps(args, ensure_ascii=False)
                    if args:
                        tool_calls[idx]["args"] += args

    if usage_info:
        try:
            from app import mistral_usage
            mistral_usage.log_usage(
                real_model,
                usage_info.get("prompt_tokens", 0),
                usage_info.get("completion_tokens", 0),
                "agent",
            )
        except Exception:
            pass

    return content, tool_calls, reasoning
