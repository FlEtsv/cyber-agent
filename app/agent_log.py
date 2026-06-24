"""
Traceability log for CyberAgent — writes to agent.log in the project root.
Import and call log() from anywhere; thread-safe.
Sensitive values (tokens, passwords, secrets) are redacted before writing.
"""
import os, re, threading, datetime, json, traceback
from collections import Counter

_SENSITIVE_KEYS = frozenset({
    "password", "password_hash", "pw", "secret", "token", "api_key",
    "access_token", "bearer", "hash", "totp_secret", "host_secret",
    "jwt_secret", "relay_host_secret", "auth", "authorization",
    "cookie", "ca_token", "key", "private_key",
})

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
_SENSITIVE_INLINE_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret|authorization|cookie|totp[_-]?secret|host[_-]?secret)\b"
    r"(\s*[:=]\s*)"
    r"([^\s,;]+)"
)


def _redact(obj):
    """Recursively redact sensitive values before serialization."""
    if isinstance(obj, dict):
        return {
            k: "[REDACTED]" if k.lower() in _SENSITIVE_KEYS else _redact(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(item) for item in obj]
    if isinstance(obj, str):
        redacted = _JWT_RE.sub("[JWT_REDACTED]", obj)
        return _SENSITIVE_INLINE_RE.sub(r"\1\2[REDACTED]", redacted)
    return obj

_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "agent.log")
_lock = threading.Lock()
_LOG_LINE_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\]\s+\[(?P<level>[A-Z]+)\]\s+\[(?P<section>[^\]]+)\]\s+(?P<msg>.*?)(?:\s+\|\s+(?P<data>.*))?$"
)


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(level: str, section: str, msg: str, data=None):
    line = f"[{_ts()}] [{level}] [{section}] {msg}"
    if data is not None:
        try:
            d = json.dumps(_redact(data), ensure_ascii=False, default=str)
            if len(d) > 300:
                d = d[:297] + "..."
            line += f"  | {d}"
        except Exception:
            line += f"  | {repr(data)[:300]}"
    with _lock:
        try:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def log_exception(section: str, msg: str = ""):
    tb = traceback.format_exc()
    log("ERROR", section, msg or "Exception", {"traceback": tb})


def clear():
    with _lock:
        try:
            with open(_LOG_PATH, "w", encoding="utf-8") as _f:
                    pass
        except Exception:
            pass


def separator(label: str = ""):
    line = f"\n{'─'*60} {label} {'─'*60}\n" if label else f"\n{'─'*120}\n"
    with _lock:
        try:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def build_report(max_lines: int = 500) -> dict:
    """Build a redacted diagnostic report from agent.log."""
    max_lines = max(1, min(int(max_lines or 500), 5000))
    with _lock:
        try:
            with open(_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-max_lines:]
        except FileNotFoundError:
            lines = []
        except Exception as exc:
            lines = [f"[report] Could not read log: {exc}\n"]

    text = "".join(lines)
    levels = {"ERROR": 0, "WARN": 0, "INFO": 0, "DEBUG": 0}
    for line in lines:
        for level in levels:
            if f"[{level}]" in line:
                levels[level] += 1

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "log_path": os.path.abspath(_LOG_PATH),
        "line_count": len(lines),
        "levels": levels,
        "text": _redact(text),
    }


def write_report(path: str, max_lines: int = 500) -> str:
    """Write a redacted JSON report and return the absolute output path."""
    report = build_report(max_lines=max_lines)
    out = os.path.abspath(path)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return out


def _parse_time(value: str) -> datetime.datetime | None:
    try:
        today = datetime.date.today()
        h, m, s_ms = value.split(":", 2)
        if "." in s_ms:
            s, ms = s_ms.split(".", 1)
        else:
            s, ms = s_ms, "0"
        return datetime.datetime(
            today.year, today.month, today.day,
            int(h), int(m), int(s), int(ms.ljust(6, "0")[:6]),
        )
    except Exception:
        return None


def parse_recent_activity(max_lines: int = 1000) -> list[dict]:
    """Parse recent agent.log lines into structured activity entries."""
    max_lines = max(1, min(int(max_lines or 1000), 5000))
    with _lock:
        try:
            with open(_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-max_lines:]
        except Exception:
            return []

    entries: list[dict] = []
    for raw in lines:
        line = raw.rstrip("\n")
        match = _LOG_LINE_RE.match(line)
        if not match:
            if line.strip():
                entries.append({
                    "ts": "",
                    "level": "INFO",
                    "section": "raw",
                    "msg": line,
                    "raw": line,
                })
            continue
        item = match.groupdict()
        item["raw"] = line
        entries.append(item)
    return entries


def summarize_activity(max_lines: int = 1000, decision_limit: int = 500) -> dict:
    """Summarize agent activity from agent.log and decision_log."""
    entries = parse_recent_activity(max_lines=max_lines)
    levels = Counter()
    error_sections = Counter()
    tool_sections = Counter()
    send_times: list[datetime.datetime] = []
    response_times: list[float] = []

    for entry in entries:
        level = entry.get("level", "INFO")
        section = entry.get("section", "raw")
        msg = entry.get("msg", "")
        ts = _parse_time(entry.get("ts", ""))

        levels[level] += 1
        if level == "ERROR":
            error_sections[section] += 1
        if section in {"main_window._on_tool_result", "main_window._on_tool_call"}:
            tool_sections[section] += 1
        if section == "main_window._send" and ts is not None:
            send_times.append(ts)
        if section == "main_window._on_finished" and ts is not None and send_times:
            start = send_times.pop(0)
            response_times.append(max((ts - start).total_seconds(), 0.0))

    top_errors = error_sections.most_common(5)
    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else None
    p50_response = round(sorted(response_times)[len(response_times) // 2], 2) if response_times else None

    top_tools: list[tuple[str, int]] = []
    try:
        from app.consciousness.decision_log import get_recent_decisions
        tool_counts = Counter(
            row.get("tool_name", "")
            for row in get_recent_decisions(limit=decision_limit)
            if row.get("tool_name")
        )
        top_tools = tool_counts.most_common(5)
    except Exception:
        top_tools = []

    return {
        "log_lines": len(entries),
        "levels": dict(levels),
        "top_errors": [{"section": section, "count": count} for section, count in top_errors],
        "top_tools": [{"tool": tool, "count": count} for tool, count in top_tools],
        "response": {
            "count": len(response_times),
            "avg_seconds": avg_response,
            "p50_seconds": p50_response,
        },
    }
