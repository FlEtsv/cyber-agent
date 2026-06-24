"""Unit tests for app/auth.py — JWT, bcrypt, TOTP, brute-force lockout."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── JWT ───────────────────────────────────────────────────────────────────────

class TestJWT:
    def test_round_trip(self):
        from app.auth import create_token, verify_token
        token = create_token("steve@test.com")
        assert isinstance(token, str) and len(token) > 20
        assert verify_token(token) == "steve@test.com"

    def test_invalid_token_returns_none(self):
        from app.auth import verify_token
        assert verify_token("not.a.valid.token") is None

    def test_tampered_token_returns_none(self):
        from app.auth import create_token, verify_token
        token = create_token("steve@test.com")
        assert verify_token(token[:-4] + "XXXX") is None


# ── Credentials + brute-force ─────────────────────────────────────────────────

@pytest.fixture()
def isolated_auth(tmp_path, monkeypatch):
    """Redirect credentials and reset brute-force counters to a clean state."""
    import app.auth as m
    monkeypatch.setattr(m, "_CREDS_FILE", tmp_path / "credentials.json")
    monkeypatch.setattr(m, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(m, "_fail_count", 0)
    monkeypatch.setattr(m, "_lockout_until", 0.0)


class TestCredentials:
    def test_not_setup_initially(self, isolated_auth):
        from app.auth import is_setup_done
        assert is_setup_done() is False

    def test_setup_creates_credentials(self, isolated_auth):
        from app.auth import setup_user, is_setup_done
        setup_user("admin@test.com", "supersecure123")
        assert is_setup_done() is True

    def test_correct_password(self, isolated_auth):
        from app.auth import setup_user, verify_password_only
        setup_user("admin@test.com", "supersecure123")
        assert verify_password_only("admin@test.com", "supersecure123") is True

    def test_wrong_password(self, isolated_auth):
        from app.auth import setup_user, verify_password_only
        setup_user("admin@test.com", "supersecure123")
        assert verify_password_only("admin@test.com", "wrong") is False

    def test_wrong_email(self, isolated_auth):
        from app.auth import setup_user, verify_password_only
        setup_user("admin@test.com", "supersecure123")
        assert verify_password_only("other@test.com", "supersecure123") is False

    def test_brute_force_locks_after_5_failures(self, isolated_auth):
        from app.auth import setup_user, verify_password_only
        setup_user("admin@test.com", "supersecure123")
        for _ in range(5):
            verify_password_only("admin@test.com", "bad")
        # Correct password should still be blocked
        assert verify_password_only("admin@test.com", "supersecure123") is False


# ── TOTP ──────────────────────────────────────────────────────────────────────

class TestTOTP:
    def test_valid_totp_login(self, isolated_auth):
        import pyotp
        from app.auth import setup_user, get_totp_secret, verify_login
        setup_user("admin@test.com", "supersecure123")
        secret = get_totp_secret()
        code = pyotp.TOTP(secret).now()
        assert verify_login("admin@test.com", "supersecure123", code) is True

    def test_wrong_totp_rejected(self, isolated_auth):
        from app.auth import setup_user, verify_login
        setup_user("admin@test.com", "supersecure123")
        assert verify_login("admin@test.com", "supersecure123", "000000") is False

    def test_wrong_password_with_valid_totp(self, isolated_auth):
        import pyotp
        from app.auth import setup_user, get_totp_secret, verify_login
        setup_user("admin@test.com", "supersecure123")
        code = pyotp.TOTP(get_totp_secret()).now()
        assert verify_login("admin@test.com", "wrongpass", code) is False
