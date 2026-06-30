"""
M-02: Tests del módulo de seguridad de CyberAgent.

Cubre: ha_tools dispatcher, training_store schema+export, notify stub,
       vault endpoints (mock), tool registration.
No activa SECURITY_ENABLED ni llama a servicios reales.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── ha_tools ─────────────────────────────────────────────────────────────────

class TestHaToolsDispatcher:
    def test_unknown_op_returns_error(self):
        from app.security.ha_tools import run
        r = run("nonexistent_op")
        assert r["ok"] is False
        assert "desconocida" in r["error"]

    def test_missing_config_returns_error(self):
        from app.security.ha_tools import run
        with patch("app.security.ha_tools._cfg", return_value=("", "")):
            r = run("turn_on", "light.test")
        assert r["ok"] is False
        assert "vault" in r["error"].lower() or "configurad" in r["error"].lower()

    def test_available_false_when_no_config(self):
        from app.security.ha_tools import available
        with patch("app.security.ha_tools._cfg", return_value=("", "")):
            assert available() is False

    def test_available_true_when_config_present(self):
        from app.security.ha_tools import available
        with patch("app.security.ha_tools._cfg", return_value=("http://ha:8123", "token123")):
            assert available() is True

    def test_speak_requires_message(self):
        from app.security.ha_tools import run
        with patch("app.security.ha_tools._cfg", return_value=("http://ha:8123", "tok")):
            with patch("app.security.ha_tools._call", return_value={"ok": True, "data": {}}):
                r = run("speak", "", {"message": "Hola mundo"})
        assert r["ok"] is True

    def test_speak_empty_message_error(self):
        from app.security.ha_tools import run
        with patch("app.security.ha_tools._cfg", return_value=("http://ha:8123", "tok")):
            r = run("speak", "")
        assert r["ok"] is False

    def test_snapshot_returns_url(self):
        from app.security.ha_tools import run
        with patch("app.security.ha_tools._cfg", return_value=("http://ha:8123", "tok")):
            r = run("snapshot", "camera.entrada")
        assert r["ok"] is True
        assert "url" in r
        assert "camera.entrada" in r["url"]

    def test_turn_on_calls_ha(self):
        from app.security.ha_tools import run
        mock_result = {"ok": True, "data": {}}
        with patch("app.security.ha_tools._cfg", return_value=("http://ha:8123", "tok")):
            with patch("app.security.ha_tools._call", return_value=mock_result) as mc:
                r = run("turn_on", "light.salon")
        assert r["ok"] is True
        mc.assert_called_once()
        call_args = mc.call_args
        assert "turn_on" in call_args[0][1]  # path contains service name

    def test_ping_op(self):
        from app.security.ha_tools import run
        with patch("app.security.ha_tools._cfg", return_value=("http://ha:8123", "tok")):
            with patch("app.security.ha_tools._call", return_value={"ok": True, "data": "ok"}) as mc:
                r = run("ping")
        mc.assert_called_once_with("GET", "/api/")
        assert r["ok"] is True


# ── training_store ────────────────────────────────────────────────────────────

class TestTrainingStore:
    def _make_store(self, tmp_path):
        """Parcha _DB_PATH a un archivo temporal."""
        import app.training_store as ts
        db = tmp_path / "test_training.db"
        return ts, db

    def test_record_and_count(self, tmp_path):
        import app.training_store as ts
        with patch.object(ts, "_DB_PATH", tmp_path / "tr.db"):
            ts._init()
            ts.record("interaction", "USER: hola", "Hola humano")
            ts.record("approval", "tool: shell", "APROBADO", 1.0)
            assert ts.count() == 2
            assert ts.count("interaction") == 1
            assert ts.count("approval") == 1

    def test_record_interaction_helper(self, tmp_path):
        import app.training_store as ts
        with patch.object(ts, "_DB_PATH", tmp_path / "tr.db"):
            ts._init()
            row_id = ts.record_interaction("¿Qué tiempo hace?", "Soleado.", "Eres un asistente.")
            assert row_id > 0

    def test_record_approval_signal(self, tmp_path):
        import app.training_store as ts
        with patch.object(ts, "_DB_PATH", tmp_path / "tr.db"):
            ts._init()
            ts.record_approval("shell", {"command": "ls"}, True)
            ts.record_approval("shell", {"command": "rm -rf /"}, False, "demasiado peligroso")
            assert ts.count("approval") == 2

    def test_stats_structure(self, tmp_path):
        import app.training_store as ts
        with patch.object(ts, "_DB_PATH", tmp_path / "tr.db"):
            ts._init()
            ts.record("interaction", "A", "B")
            ts.record("feedback", "A", "B", 1.0)
            s = ts.stats()
            assert "total" in s
            assert "by_kind" in s
            assert s["total"] == 2
            assert "interaction" in s["by_kind"]

    def test_export_jsonl(self, tmp_path):
        import app.training_store as ts
        with patch.object(ts, "_DB_PATH", tmp_path / "tr.db"):
            ts._init()
            ts.record_interaction("Dime hola", "Hola Steve.", "Eres CyberAgent.")
            ts.record_interaction("¿Qué hora es?", "Son las 12:00.")
            out = ts.export(tmp_path / "out.jsonl")
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 2
            obj = json.loads(lines[0])
            assert "messages" in obj
            roles = [m["role"] for m in obj["messages"]]
            assert "user" in roles
            assert "assistant" in roles

    def test_export_filter_by_kind(self, tmp_path):
        import app.training_store as ts
        with patch.object(ts, "_DB_PATH", tmp_path / "tr.db"):
            ts._init()
            ts.record("interaction", "A", "B")
            ts.record("approval", "C", "D", 1.0)
            out = ts.export(tmp_path / "out2.jsonl", kind="interaction")
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 1

    def test_export_filter_by_signal(self, tmp_path):
        import app.training_store as ts
        with patch.object(ts, "_DB_PATH", tmp_path / "tr.db"):
            ts._init()
            ts.record("feedback", "A", "B", 1.0)
            ts.record("feedback", "C", "D", -1.0)
            out = ts.export(tmp_path / "out3.jsonl", min_signal=0.0)
            lines = [l for l in out.read_text(encoding="utf-8").strip().splitlines() if l]
            assert len(lines) == 1


# ── notify stub ──────────────────────────────────────────────────────────────

class TestSecurityNotify:
    def test_available_false_without_token(self):
        from app.security.notify import available
        with patch("app.security.notify._cfg", return_value=(None, None)):
            assert available() is False

    def test_available_true_with_token(self):
        from app.security.notify import available
        with patch("app.security.notify._cfg", return_value=("tok123", "12345678")):
            assert available() is True

    def test_send_returns_error_on_no_cfg(self):
        from app.security.notify import send
        with patch("app.security.notify._cfg", return_value=(None, None)):
            r = send("test")
        assert r["ok"] is False


# ── tool registration ─────────────────────────────────────────────────────────

class TestToolRegistration:
    def test_ha_control_in_schema(self):
        from app.tools import TOOLS_SCHEMA
        names = [t["function"]["name"] for t in TOOLS_SCHEMA]
        assert "ha_control" in names

    def test_ha_control_is_dangerous(self):
        from app.tools import DANGEROUS_TOOLS
        assert "ha_control" in DANGEROUS_TOOLS

    def test_ha_in_tool_categories(self):
        from app.tools import TOOL_CATEGORIES
        assert "ha" in TOOL_CATEGORIES
        assert "ha_control" in TOOL_CATEGORIES["ha"]

    def test_ha_in_tool_router_categories(self):
        from app.tool_router import CATEGORIES
        assert "ha" in CATEGORIES
        assert "ha_control" in CATEGORIES["ha"]

    def test_docker_update_op_in_schema(self):
        from app.tools import TOOLS_SCHEMA
        docker_schema = next(t for t in TOOLS_SCHEMA if t["function"]["name"] == "docker")
        op_desc = docker_schema["function"]["parameters"]["properties"]["op"]["description"]
        assert "update" in op_desc


# ── DockerHAService ───────────────────────────────────────────────────────────

class TestDockerHAService:
    def test_skipped_when_disabled(self):
        from app.supervisor import DockerHAService
        svc = DockerHAService()
        with patch.dict(os.environ, {"CYBERAGENT_SECURITY_ENABLED": "0"}):
            ok, msg = svc.check()
        assert ok is True
        assert "skipped" in msg

    def test_ok_when_container_running(self):
        from app.supervisor import DockerHAService
        svc = DockerHAService()
        mock_containers = [{"name": "homeassistant", "state": "running", "status": "Up"}]
        with patch.dict(os.environ, {"CYBERAGENT_SECURITY_ENABLED": "1"}):
            with patch("app.supervisor.DockerHAService.check",
                       return_value=(True, "ha_docker=running (homeassistant)")):
                ok, msg = svc.check()
        assert ok is True
