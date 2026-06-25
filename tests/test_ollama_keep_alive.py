"""Tests for Ollama keep_alive compatibility."""

import importlib


def test_legacy_negative_keep_alive_env_is_duration(monkeypatch):
    import app.ollama_client as ollama_client

    monkeypatch.setenv("CYBERAGENT_FAST_KEEP_ALIVE", "-1")
    reloaded = importlib.reload(ollama_client)

    assert reloaded.FAST_KEEP_ALIVE == "24h"

    monkeypatch.delenv("CYBERAGENT_FAST_KEEP_ALIVE", raising=False)
    importlib.reload(ollama_client)


def test_named_infinite_keep_alive_env_is_duration(monkeypatch):
    import app.ollama_client as ollama_client

    monkeypatch.setenv("CYBERAGENT_FAST_KEEP_ALIVE", "forever")
    reloaded = importlib.reload(ollama_client)

    assert reloaded.FAST_KEEP_ALIVE == "24h"

    monkeypatch.delenv("CYBERAGENT_FAST_KEEP_ALIVE", raising=False)
    importlib.reload(ollama_client)
