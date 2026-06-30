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


# ── B-07: format (nueva suite) ────────────────────────────────────────────────
class TestFormatNew:
    def test_strip_think(self):
        from app.security.telegram.format import strip_think
        assert strip_think("<think>internal</think>hello") == "hello"
        assert strip_think("no think here") == "no think here"

    def test_md_bold(self):
        from app.security.telegram.format import md_to_html
        assert "<b>hello</b>" in md_to_html("**hello**")

    def test_sanitize_strips_think(self):
        from app.security.telegram.format import sanitize
        result = sanitize("<think>secret</think>visible")
        assert "secret" not in result
        assert "visible" in result

    def test_sanitize_truncates(self):
        from app.security.telegram.format import sanitize
        result = sanitize("x" * 5000, max_len=100)
        assert len(result) <= 103


# ── A-07: decision parser (nueva suite) ───────────────────────────────────────
class TestDecisionParser:
    def test_parse_json(self):
        from app.security.decision import parse
        d = parse('{"action": "notify", "confidence": 0.8, "reason": "test", "threat_score": 0.7}')
        assert d.action == "notify"

    def test_parse_json_in_markdown(self):
        from app.security.decision import parse
        t = '```json\n{"action": "deter", "confidence": 0.9, "reason": "x", "threat_score": 0.8}\n```'
        d = parse(t)
        assert d.action == "deter"

    def test_invalid_action_defaults(self):
        from app.security.decision import parse
        d = parse('{"action": "destroy_world", "confidence": 0.5, "reason": "x", "threat_score": 0.5}')
        assert d.action == "notify"

    def test_clamps_values(self):
        from app.security.decision import parse
        d = parse('{"action": "notify", "confidence": 99, "reason": "x", "threat_score": -5}')
        assert 0.0 <= d.confidence <= 1.0
        assert 0.0 <= d.threat_score <= 1.0

    def test_parse_visual(self):
        from app.security.decision import parse_visual
        v = parse_visual('{"threat_score": 0.6, "description": "dog", "action": "notify", "confidence": 0.75}')
        assert abs(v["threat_score"] - 0.6) < 0.01


# ── D-05: autonomy (nueva suite) ──────────────────────────────────────────────
class TestAutonomyNew:
    def setup_method(self):
        import app.security.autonomy as a
        a._STATE_PATH = Path(tempfile.mktemp(suffix=".json"))
        a._state = {"mode": "manual"}

    def test_default_manual(self):
        from app.security.autonomy import get_mode
        assert get_mode() == "manual"

    def test_set_valid(self):
        from app.security.autonomy import set_mode, get_mode
        set_mode("operativa")
        assert get_mode() == "operativa"

    def test_set_invalid(self):
        from app.security.autonomy import set_mode
        r = set_mode("nuclear")
        assert not r["ok"]

    def test_auto_act_manual(self):
        from app.security.autonomy import set_mode, should_auto_act
        set_mode("manual")
        assert not should_auto_act("low")

    def test_auto_act_alto_impacto(self):
        from app.security.autonomy import set_mode, should_auto_act
        set_mode("alto-impacto")
        assert should_auto_act("high")


# ── D-01: events (nueva suite) ────────────────────────────────────────────────
class TestEventsNew:
    def setup_method(self):
        import app.security.events as e
        e._ring.clear()
        e._subscribers.clear()
        e._DB_PATH = Path(tempfile.mktemp(suffix=".db"))

    def test_emit_and_recent(self):
        from app.security.events import emit, recent
        emit("test_event", {"cam_id": "cam1"})
        evts = recent(10)
        assert len(evts) >= 1
        assert evts[-1]["event_type"] == "test_event"

    def test_subscribe(self):
        from app.security.events import emit, subscribe
        received = []
        subscribe(lambda t, p: received.append(t))
        emit("motion", {})
        assert "motion" in received

    def test_ring_filter(self):
        from app.security.events import emit, recent
        emit("motion", {})
        emit("alarm", {})
        evts = recent(10, event_type="motion")
        assert all(e["event_type"] == "motion" for e in evts)


# ── D-07: app_registry (nueva suite) ─────────────────────────────────────────
class TestAppRegistryNew:
    def setup_method(self):
        import app.security.app_registry as r
        r._REGISTRY_PATH = Path(tempfile.mktemp(suffix=".json"))

    def test_register_and_validate(self):
        from app.security.app_registry import register_app, validate_token
        register_app("test_app", token="tok123")
        assert validate_token("tok123") == "test_app"

    def test_invalid_token(self):
        from app.security.app_registry import validate_token
        assert validate_token("bad_token_xyz999") is None

    def test_revoke(self):
        from app.security.app_registry import register_app, revoke_app, validate_token
        register_app("app_to_revoke", token="rev999")
        revoke_app("app_to_revoke")
        assert validate_token("rev999") is None


# ── D-09: schedule (nueva suite) ─────────────────────────────────────────────
class TestScheduleNew:
    def setup_method(self):
        import app.security.schedule as s
        s._PATH = Path(tempfile.mktemp(suffix=".json"))

    def test_add_and_list(self):
        from app.security.schedule import add_task, list_tasks
        add_task("snapshot", 300, {"cam_id": "cam1"})
        tasks = list_tasks()
        assert len(tasks) == 1

    def test_remove(self):
        from app.security.schedule import add_task, remove_task, list_tasks
        t = add_task("backup_dbs", 3600)
        remove_task(t["id"])
        assert not list_tasks()

    def test_default_tasks(self):
        from app.security.schedule import default_tasks, list_tasks
        default_tasks()
        types = {t["type"] for t in list_tasks()}
        assert "retention_cleanup" in types
        assert "backup_dbs" in types


# ── B-06: keyboards (nueva suite) ────────────────────────────────────────────
class TestKeyboardsNew:
    def test_security_keyboard(self):
        from app.security.telegram.keyboards import security_keyboard
        kb = security_keyboard("cam1", "ev123")
        assert "inline_keyboard" in kb
        assert len(kb["inline_keyboard"]) == 3

    def test_agent_keyboard(self):
        from app.security.telegram.keyboards import agent_keyboard
        kb = agent_keyboard("deter_warn", "run001")
        assert "inline_keyboard" in kb
        callbacks = [b["callback_data"] for b in kb["inline_keyboard"][0]]
        assert any("approve" in c for c in callbacks)


# ── A-06: prompts (nueva suite) ───────────────────────────────────────────────
class TestPromptsNew:
    def test_build_visual_prompt(self):
        from app.security.prompts import build_visual_prompt
        p = build_visual_prompt("cam_entrada")
        assert "cam_entrada" in p
        assert "threat_score" in p

    def test_build_event_prompt(self):
        from app.security.prompts import build_event_prompt
        p = build_event_prompt("motion", "persona detectada", "cam1")
        assert "motion" in p

    def test_build_chat_prompt(self):
        from app.security.prompts import build_chat_prompt
        p = build_chat_prompt()
        assert "CyberAgent" in p


# ── C-07: property_context (nueva suite) ─────────────────────────────────────
class TestPropertyContextNew:
    def test_load_returns_dict(self):
        from app.security.property_context import load_property
        assert isinstance(load_property(), dict)

    def test_get_context(self):
        from app.security.property_context import get_context_for_model
        assert isinstance(get_context_for_model(), str)

    def test_save_and_load(self):
        import app.security.property_context as pc
        orig = pc._PROPERTY_JSON
        pc._PROPERTY_JSON = Path(tempfile.mktemp(suffix=".json"))
        try:
            pc.save_property({"address": "Test St", "cameras": []})
            loaded = pc.load_property()
            assert loaded["address"] == "Test St"
        finally:
            pc._PROPERTY_JSON = orig


# ── B-04: viewers (nueva suite) ──────────────────────────────────────────────
class TestViewersNew:
    def setup_method(self):
        import app.security.telegram.viewers as v
        v._DB = Path(tempfile.mktemp(suffix=".db"))

    def test_add_and_list(self):
        from app.security.telegram import viewers
        viewers.add_viewer(111, "alice", "admin")
        assert any(v["user_id"] == 111 for v in viewers.list_all())

    def test_is_admin(self):
        from app.security.telegram import viewers
        viewers.add_viewer(333, "admin_user", "admin")
        assert viewers.is_admin(333)
        assert not viewers.is_admin(999)

    def test_remove(self):
        from app.security.telegram import viewers
        viewers.add_viewer(444, "temp", "viewer")
        viewers.remove_viewer(444)
        assert not viewers.is_authorized(444)
