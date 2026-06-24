"""
Traceability log for CyberAgent — writes to agent.log in the project root.
Import and call log() from anywhere; thread-safe.
Sensitive values (tokens, passwords, secrets) are redacted before writing.
"""
import os, re, threading, datetime, json, traceback

_SENSITIVE_KEYS = frozenset({
    "password", "password_hash", "pw", "secret", "token", "api_key",
    "access_token", "bearer", "hash", "totp_secret", "host_secret",
    "jwt_secret", "relay_host_secret", "auth", "authorization",
    "cookie", "ca_token", "key", "private_key",
})

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")


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
        return _JWT_RE.sub("[JWT_REDACTED]", obj)
    return obj

_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "agent.log")
_lock = threading.Lock()


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
