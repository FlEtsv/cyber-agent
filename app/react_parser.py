"""
ReAct-style tool calling parser.
Models that lack native function-calling training output:
    <tool_call>{"name": "shell", "args": {"command": "ls"}}</tool_call>
We parse these tags, execute the tools, and feed results back.
"""
import re, json
from app.tools import TOOLS_SCHEMA

# Pattern that matches <tool_call>...</tool_call> (possibly multiline)
_PATTERN = re.compile(r'<tool_call>(.*?)</tool_call>', re.DOTALL | re.IGNORECASE)


def build_tools_system_block() -> str:
    """Generate the tool-calling instructions injected into the system prompt."""
    lines = [
        "\n\n## SISTEMA DE HERRAMIENTAS",
        "Cuando necesites ejecutar algo, escribe uno o más bloques tool_call en tu respuesta:",
        "",
        '<tool_call>{"name": "nombre_herramienta", "args": {"param": "valor"}}</tool_call>',
        "",
        "Puedes encadenar varias llamadas. El sistema ejecutará cada una y te devolverá el resultado.",
        "NO expliques que vas a llamar la herramienta, hazlo directamente.",
        "",
        "### HERRAMIENTAS DISPONIBLES",
    ]

    for tool in TOOLS_SCHEMA:
        fn   = tool["function"]
        name = fn["name"]
        desc = fn["description"].split("\n")[0]  # first line only
        props    = fn.get("parameters", {}).get("properties", {})
        required = fn.get("parameters", {}).get("required", [])

        lines.append(f"\n**{name}** — {desc}")
        if props:
            param_strs = []
            for pname, pdef in props.items():
                req  = "*" if pname in required else ""
                pdesc = pdef.get("description", "")
                param_strs.append(f"{req}{pname}: {pdesc}")
            lines.append("  Parámetros: " + " | ".join(param_strs[:6]))

    lines += [
        "",
        "### EJEMPLOS",
        '<tool_call>{"name": "shell", "args": {"command": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5"}}</tool_call>',
        '<tool_call>{"name": "read_file", "args": {"path": "C:\\\\Users\\\\steve\\\\documento.txt"}}</tool_call>',
        '<tool_call>{"name": "gpu_info", "args": {}}</tool_call>',
    ]
    return "\n".join(lines)


def extract_tool_calls(text: str) -> tuple[str, dict]:
    """
    Extract <tool_call> blocks from model output.
    Returns (clean_text, tool_calls_dict).
    tool_calls_dict: {index: {"name": str, "args": str (JSON)}}
    """
    matches = list(_PATTERN.finditer(text))
    if not matches:
        return text, {}

    tool_calls = {}
    for i, m in enumerate(matches):
        raw = m.group(1).strip()
        # Some models wrap in extra braces or add trailing commas
        raw = _fix_json(raw)
        try:
            data = json.loads(raw)
            name = data.get("name", "")
            args = data.get("args", data.get("arguments", data.get("parameters", {})))
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            tool_calls[i] = {"name": name, "args_str": json.dumps(args, ensure_ascii=False)}
        except Exception:
            pass

    # Remove tool_call tags from the visible text
    clean = _PATTERN.sub("", text).strip()
    # Clean up extra blank lines left by removal
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

    return clean, tool_calls


def _fix_json(s: str) -> str:
    """Best-effort repair of slightly malformed JSON."""
    # Remove trailing commas before } or ]
    s = re.sub(r',\s*([}\]])', r'\1', s)
    # Some models add an extra } at the very end — detect by brace imbalance
    opens  = s.count('{') - s.count('}')
    if opens < 0:
        # More } than { — strip the excess from the right
        for _ in range(-opens):
            idx = s.rfind('}')
            if idx != -1:
                s = s[:idx] + s[idx+1:]
    return s


def format_tool_result(name: str, result: dict) -> str:
    """Format a tool result for injection back into the conversation."""
    result_str = json.dumps(result, ensure_ascii=False, indent=2)
    if len(result_str) > 4000:
        result_str = result_str[:4000] + "\n... [truncado]"
    return f"<tool_result name=\"{name}\">\n{result_str}\n</tool_result>"
