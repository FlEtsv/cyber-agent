"""Auth layer: bcrypt passwords, TOTP 2FA, JWT sessions."""
import json, os, secrets, time, threading
from pathlib import Path

import bcrypt
import pyotp
import qrcode
import qrcode.image.svg
from jose import jwt, JWTError

# ── Config ────────────────────────────────────────────────────────────────────
_DATA_DIR  = Path(__file__).parent.parent / "data"
_CREDS_FILE = _DATA_DIR / "credentials.json"
_SECRET_FILE = _DATA_DIR / "jwt_secret.txt"
_DATA_DIR.mkdir(exist_ok=True)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72

def _jwt_secret() -> str:
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    s = secrets.token_hex(32)
    _SECRET_FILE.write_text(s)
    try:
        os.chmod(str(_SECRET_FILE), 0o600)
    except OSError:
        pass
    return s

JWT_SECRET = _jwt_secret()

# ── Brute-force protection ────────────────────────────────────────────────────
_FAIL_LOCK     = threading.Lock()
_fail_count    = 0
_lockout_until = 0.0
_MAX_FAILS     = 5
_LOCKOUT_SECS  = 60


def _check_lockout() -> bool:
    """Returns True if currently locked out."""
    with _FAIL_LOCK:
        return time.time() < _lockout_until


def _record_failure():
    global _fail_count, _lockout_until
    with _FAIL_LOCK:
        _fail_count += 1
        if _fail_count >= _MAX_FAILS:
            _lockout_until = time.time() + _LOCKOUT_SECS
            _fail_count    = 0


def _record_success():
    global _fail_count, _lockout_until
    with _FAIL_LOCK:
        _fail_count    = 0
        _lockout_until = 0.0


# ── Credentials file ──────────────────────────────────────────────────────────

def _load() -> dict:
    if _CREDS_FILE.exists():
        try:
            return json.loads(_CREDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save(data: dict):
    _CREDS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── User management ───────────────────────────────────────────────────────────

def is_setup_done() -> bool:
    data = _load()
    return bool(data.get("email") and data.get("password_hash"))

def setup_user(email: str, password: str) -> str:
    """First-time setup. Returns the TOTP provisioning URI."""
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    totp_secret = pyotp.random_base32()
    totp = pyotp.TOTP(totp_secret)
    uri  = totp.provisioning_uri(name=email, issuer_name="CyberAgent")
    _save({"email": email, "password_hash": pw_hash, "totp_secret": totp_secret})
    return uri

def verify_login(email: str, password: str, totp_code: str) -> bool:
    if _check_lockout():
        return False
    data = _load()
    if data.get("email") != email:
        _record_failure()
        return False
    if not bcrypt.checkpw(password.encode(), data["password_hash"].encode()):
        _record_failure()
        return False
    totp = pyotp.TOTP(data["totp_secret"])
    ok = totp.verify(totp_code, valid_window=1)
    if ok:
        _record_success()
    else:
        _record_failure()
    return ok

def verify_password_only(email: str, password: str) -> bool:
    if _check_lockout():
        return False
    data = _load()
    if data.get("email") != email:
        _record_failure()
        return False
    ok = bcrypt.checkpw(password.encode(), data["password_hash"].encode())
    if ok:
        _record_success()
    else:
        _record_failure()
    return ok

def get_totp_secret() -> str:
    return _load().get("totp_secret", "")

def get_totp_qr_svg(email: str) -> str:
    secret = get_totp_secret()
    totp = pyotp.TOTP(secret)
    uri  = totp.provisioning_uri(name=email, issuer_name="CyberAgent")
    qr   = qrcode.make(uri, image_factory=qrcode.image.svg.SvgImage)
    import io
    buf = io.BytesIO()
    qr.save(buf)
    return buf.getvalue().decode()


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(email: str) -> str:
    payload = {
        "sub": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> str | None:
    """Returns email if valid, None otherwise."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
