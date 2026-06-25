"""Integration tests for the Cloud Run relay bridge."""

import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test-relay-secret")
os.environ.setdefault("TOTP_OPTIONAL", "1")

import pytest
from fastapi.testclient import TestClient

import relay.main as relay


@pytest.fixture()
def relay_client(monkeypatch):
    monkeypatch.setattr(relay, "HOST_SECRET", "host-secret")
    relay.state.host_ws = None
    relay.state.host_q = asyncio.Queue(maxsize=100)
    relay.state.sessions.clear()
    relay.state._send_fn = None
    relay.state._models = []
    relay.state._active_model = ""
    relay.state._buffers.clear()
    relay.state._ping_miss = 0
    if relay.state._ping_task is not None:
        relay.state._ping_task.cancel()
        relay.state._ping_task = None

    client = TestClient(relay.app)
    client.cookies.set("ca_token", relay._make_token("steve@test.local"))
    try:
        yield client
    finally:
        relay.state.host_ws = None
        relay.state.sessions.clear()
        relay.state._send_fn = None
        relay.state._models = []
        relay.state._active_model = ""
        relay.state._buffers.clear()
        if relay.state._ping_task is not None:
            relay.state._ping_task.cancel()
            relay.state._ping_task = None


def test_mobile_session_reports_pc_offline(relay_client):
    with relay_client.websocket_connect("/ws") as mobile:
        connected = mobile.receive_json()
        assert connected["type"] == "connected"
        assert connected["data"]["pc_online"] is False
        assert connected["data"]["session_id"]

        offline = mobile.receive_json()
        assert offline["type"] == "error"
        assert "PC" in offline["data"]

        mobile.send_json({"type": "message", "content": "hola"})
        no_pc = mobile.receive_json()
        assert no_pc == {"type": "error", "data": "PC no conectado"}


def test_relay_bridges_models_messages_approvals_and_history(relay_client):
    with relay_client.websocket_connect("/host?secret=host-secret") as host:
        host.send_json({
            "type": "models",
            "models": ["cyberagent-original:latest", "power-model:latest"],
            "active": "cyberagent-original:latest",
        })

        with relay_client.websocket_connect("/ws") as mobile:
            connected = mobile.receive_json()
            session_id = connected["data"]["session_id"]
            assert connected["data"]["pc_online"] is True
            assert connected["data"]["models"] == [
                "cyberagent-original:latest",
                "power-model:latest",
            ]

            mobile.send_json({
                "type": "message",
                "content": "resume estado",
                "model": "power",
                "session_trust": True,
                "permissions": {"read_file": "auto"},
            })
            forwarded = host.receive_json()
            assert forwarded["type"] == "message"
            assert forwarded["session_id"] == session_id
            assert forwarded["content"] == "resume estado"
            assert forwarded["model"] == "power"
            assert forwarded["session_trust"] is True
            assert forwarded["permissions"] == {"read_file": "auto"}

            mobile.send_json({"type": "approve", "tool_id": "tool-1", "approved": True})
            approval = host.receive_json()
            assert approval == {
                "type": "approve",
                "tool_id": "tool-1",
                "approved": True,
                "session_id": session_id,
            }

            host.send_json({"type": "token", "session_id": session_id, "data": "ok"})
            assert mobile.receive_json() == {"type": "token", "data": "ok"}
            host.send_json({"type": "done", "session_id": session_id, "data": {}})
            assert mobile.receive_json() == {"type": "done", "data": {}}

            history = relay_client.get(f"/api/session/{session_id}/history")
            assert history.status_code == 200
            events = history.json()
            assert {"type": "user_message", "content": "resume estado", "ts": events[0]["ts"]} in events
            assert {"type": "token", "data": "ok"} in events
            assert {"type": "done", "data": {}} in events

            mobile.send_json({"type": "get_history"})
            history_event = mobile.receive_json()
            assert history_event["type"] == "history"
            assert history_event["data"] == events
