import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mistral_client import consult_mistral, redact_for_cloud


def test_redact_for_cloud_masks_common_secrets():
    text = (
        "api_key=abc123SECRET password: hunter2 "
        "Authorization: Bearer tokenvalue1234567890 "
        "https://example.test/?token=secretvalue"
    )

    redacted = redact_for_cloud(text)

    assert "abc123SECRET" not in redacted
    assert "hunter2" not in redacted
    assert "tokenvalue1234567890" not in redacted
    assert "secretvalue" not in redacted
    assert "<redacted>" in redacted


def test_consult_mistral_without_key_is_local_error(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_STUDIO_API_KEY", raising=False)

    result = consult_mistral("review this")

    assert result["ok"] is False
    assert "MISTRAL_API_KEY" in result["error"]
    assert result["redacted"] is True


def test_consult_mistral_redacts_payload_by_default(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {
                "choices": [{"message": {"content": "looks good"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            }

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeResponse()

    monkeypatch.setenv("MISTRAL_API_KEY", "test-secret-key")
    monkeypatch.setenv("MISTRAL_BASE_URL", "https://api.test/v1")
    monkeypatch.setattr("app.mistral_client.httpx.post", fake_post)

    result = consult_mistral(
        "audit api_key=SHOULD_NOT_LEAK",
        context="password=ALSO_SECRET",
        mode="audit",
    )

    body = captured["json"]["messages"][1]["content"]
    assert result["ok"] is True
    assert result["response"] == "looks good"
    assert "SHOULD_NOT_LEAK" not in body
    assert "ALSO_SECRET" not in body
    assert captured["headers"]["Authorization"] == "Bearer test-secret-key"
    assert "test-secret-key" not in str(result)
