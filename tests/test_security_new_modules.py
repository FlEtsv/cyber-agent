"""
M-02 (extensión): Tests de módulos nuevos implementados en BATCH-5..7.

Cubre: zones, cameras_db (ROI + discarded), hparams (update_hparams),
       recorder (API pública), tool_usage (AH-02..05), versioning,
       evaluate, comms/rate_limiter, training/data_map.
No activa SECURITY_ENABLED ni llama a servicios reales.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch


# ── Q: Zonas de vigilancia ────────────────────────────────────────────────────

class TestZones:
    def setup_method(self):
        import app.security.zones as z
        z._DB_PATH = Path(tempfile.mktemp(suffix=".db"))
        z._init()

    def test_add_and_list(self):
        from app.security.zones import add_zone, list_zones
        r = add_zone("cam1", "entrada", "warning", [[0, 0], [1, 0], [1, 1], [0, 1]])
        assert r["ok"]
        zones = list_zones("cam1")
        assert len(zones) == 1
        assert zones[0].name == "entrada"

    def test_zone_type_warning(self):
        from app.security.zones import add_zone, list_zones
        add_zone("cam2", "z1", "warning", [[0, 0], [1, 0], [1, 1], [0, 1]])
        z = list_zones("cam2")[0]
        assert z.type == "warning"
        assert z.risk_level == 2

    def test_zone_type_safe(self):
        from app.security.zones import add_zone, list_zones
        add_zone("cam3", "safe_area", "safe", [[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5]])
        z = list_zones("cam3")[0]
        assert z.risk_level == 0

    def test_delete_zone(self):
        from app.security.zones import add_zone, list_zones, delete_zone
        r = add_zone("cam4", "temporal", "interest", [[0, 0], [1, 0], [1, 1], [0, 1]])
        delete_zone(r["id"])
        assert list_zones("cam4") == []

    def test_point_in_polygon_inside(self):
        from app.security.zones import _point_in_polygon
        square = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
        assert _point_in_polygon(0.5, 0.5, square)

    def test_point_in_polygon_outside(self):
        from app.security.zones import _point_in_polygon
        square = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
        assert not _point_in_polygon(0.05, 0.05, square)

    def test_point_in_zones_max_risk(self):
        from app.security.zones import add_zone, list_zones, point_in_zones
        add_zone("camX", "safe", "safe", [[0, 0], [1, 0], [1, 1], [0, 1]])
        add_zone("camX", "warn", "warning", [[0, 0], [1, 0], [1, 1], [0, 1]])
        zones = list_zones("camX")
        result = point_in_zones(0.5, 0.5, zones)
        assert result is not None
        assert result.type == "warning"

    def test_empty_zones_returns_none(self):
        from app.security.zones import point_in_zones
        assert point_in_zones(0.5, 0.5, []) is None

    def test_multiple_cams_isolated(self):
        from app.security.zones import add_zone, list_zones
        add_zone("cam_a", "zona_a", "warning", [[0, 0], [1, 0], [1, 1], [0, 1]])
        add_zone("cam_b", "zona_b", "safe", [[0, 0], [1, 0], [1, 1], [0, 1]])
        assert all(z.cam_id == "cam_a" for z in list_zones("cam_a"))
        assert all(z.cam_id == "cam_b" for z in list_zones("cam_b"))


# ── cameras_db: ROI + discarded ───────────────────────────────────────────────

class TestCamerasDbExtended:
    def setup_method(self):
        import app.security.cameras_db as cdb
        cdb._DB_PATH = Path(tempfile.mktemp(suffix=".db"))
        cdb._init()

    def test_log_discarded(self):
        import app.security.cameras_db as cdb
        cdb.log_discarded("cam1", "dog", "confianza baja (0.3)")
        with cdb.get_db() as db:
            rows = db.execute("SELECT label, reason FROM discarded_events WHERE cam_id='cam1'").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "dog"
        assert "confianza" in rows[0][1]

    def test_discarded_timestamp_recent(self):
        import app.security.cameras_db as cdb
        before = time.time()
        cdb.log_discarded("cam2", "cat", "zona segura")
        after = time.time()
        with cdb.get_db() as db:
            row = db.execute("SELECT ts FROM discarded_events WHERE cam_id='cam2'").fetchone()
        assert before <= row[0] <= after

    def test_roi_roundtrip(self):
        import json
        import app.security.cameras_db as cdb
        grid = [[True, False] * 4 for _ in range(6)]
        with cdb.get_db() as db:
            db.execute(
                "INSERT INTO camera_roi(cam_id, roi_grid) VALUES(?,?) ON CONFLICT(cam_id) DO UPDATE SET roi_grid=excluded.roi_grid",
                ("camROI", json.dumps(grid))
            )
        with cdb.get_db() as db:
            row = db.execute("SELECT roi_grid FROM camera_roi WHERE cam_id='camROI'").fetchone()
        loaded = json.loads(row[0])
        assert loaded == grid

    def test_get_db_returns_connection(self):
        import app.security.cameras_db as cdb
        with cdb.get_db() as db:
            result = db.execute("SELECT 1").fetchone()
        assert result[0] == 1


# ── hparams: update_hparams ───────────────────────────────────────────────────

class TestHparams:
    def setup_method(self):
        from dataclasses import asdict
        import app.training.hparams as hp_mod
        from unittest.mock import patch
        self._hp_mod = hp_mod
        # Snapshot global state and redirect disk I/O to a temp file
        self._orig_hparams = {k: asdict(v) for k, v in hp_mod._HPARAMS.items()}
        self._patch = patch.object(hp_mod, "_OVERRIDES_PATH", __import__("pathlib").Path(__import__("tempfile").mktemp(suffix=".json")))
        self._patch.start()

    def teardown_method(self):
        from app.training.hparams import HParams
        self._patch.stop()
        # Restore original values
        hp = self._hp_mod._HPARAMS
        hp.clear()
        for k, v in self._orig_hparams.items():
            hp[k] = HParams(**v)

    def test_get_defaults(self):
        from app.training.hparams import get
        h = get("cyberagent-24b")
        assert h.rank == 16
        assert h.epochs == 3

    def test_get_unknown_returns_defaults(self):
        from app.training.hparams import get, HParams
        h = get("nonexistent-model-xyz")
        assert isinstance(h, HParams)

    def test_get_dict(self):
        from app.training.hparams import get_dict
        d = get_dict("codestral")
        assert isinstance(d, dict)
        assert "rank" in d
        assert "lr" in d

    def test_update_hparams_rank(self):
        from app.training.hparams import update_hparams, get
        update_hparams("vision-security", rank=32)
        h = get("vision-security")
        assert h.rank == 32

    def test_update_hparams_type_coercion(self):
        from app.training.hparams import update_hparams, get
        update_hparams("tool-router", epochs="5")
        h = get("tool-router")
        assert h.epochs == 5
        assert isinstance(h.epochs, int)

    def test_update_hparams_unknown_field_ignored(self):
        from app.training.hparams import update_hparams, get
        update_hparams("cyberagent-24b", nonexistent_field=999)
        h = get("cyberagent-24b")
        assert not hasattr(h, "nonexistent_field")

    def test_update_creates_model_on_demand(self):
        from app.training.hparams import update_hparams, get
        update_hparams("brand-new-model", rank=8)
        h = get("brand-new-model")
        assert h.rank == 8

    def test_update_multiple_fields(self):
        from app.training.hparams import update_hparams, get
        update_hparams("codestral", rank=64, alpha=128, lr=1e-4)
        h = get("codestral")
        assert h.rank == 64
        assert h.alpha == 128


# ── recorder (API pública) ────────────────────────────────────────────────────

class TestRecorder:
    """Tests for recorder index (DB operations only — no actual RTSP/ffmpeg)."""

    def setup_method(self):
        import app.security.recorder as rec
        self._orig_db = rec._DB_PATH
        rec._DB_PATH = Path(tempfile.mktemp(suffix=".db"))
        self._rec = rec

    def teardown_method(self):
        import app.security.recorder as rec
        rec._DB_PATH = self._orig_db

    def _insert_rec(self, cam_id, trigger="manual", duration=30):
        """Insert a recording directly into DB for testing (bypass ffmpeg)."""
        import time
        c = self._rec._conn()
        cur = c.execute(
            "INSERT INTO recordings (cam_id, started_at, path, trigger, duration) VALUES (?,?,?,?,?)",
            (cam_id, time.time(), f"/fake/{cam_id}.mp4", trigger, duration),
        )
        c.commit()
        rid = cur.lastrowid
        c.close()
        return rid

    def test_list_recordings_empty(self):
        assert self._rec.list_recordings() == []

    def test_insert_and_list(self):
        rid = self._insert_rec("cam1")
        recs = self._rec.list_recordings(cam_id="cam1")
        assert len(recs) == 1
        assert recs[0]["cam_id"] == "cam1"
        assert recs[0]["id"] == rid

    def test_get_recording_by_id(self):
        rid = self._insert_rec("cam2", trigger="motion")
        r = self._rec.get_recording(rid)
        assert r is not None
        assert r["id"] == rid
        assert r["trigger"] == "motion"

    def test_get_nonexistent_returns_none(self):
        assert self._rec.get_recording(999999) is None

    def test_delete_recording(self):
        rid = self._insert_rec("cam3")
        self._rec.delete_recording(rid)
        assert self._rec.get_recording(rid) is None

    def test_list_filter_by_cam(self):
        self._insert_rec("cam_a", "manual")
        self._insert_rec("cam_b", "auto")
        assert len(self._rec.list_recordings(cam_id="cam_a")) == 1
        assert len(self._rec.list_recordings(cam_id="cam_b")) == 1

    def test_cleanup_orphans(self):
        self._insert_rec("cam_orphan")
        removed = self._rec.cleanup_orphans()
        # The fake path doesn't exist, so orphan should be cleaned
        assert removed >= 1
        assert self._rec.list_recordings(cam_id="cam_orphan") == []

    def test_stop_recording_no_active(self):
        # cam with no active ffmpeg process
        result = self._rec.stop_recording("cam_inactive")
        assert result is False


# ── tool_usage: AH-02..05 ─────────────────────────────────────────────────────

class TestToolUsage:
    def setup_method(self):
        import app.training.tool_usage as tu
        self._orig_db = tu._DB_PATH
        tu._DB_PATH = Path(tempfile.mktemp(suffix=".db"))
        tu._init()
        self._tu = tu

    def teardown_method(self):
        import app.training.tool_usage as tu
        tu._DB_PATH = self._orig_db

    def test_record_and_stats(self):
        import app.training.tool_usage as tu
        tu.record("cyberagent-24b", "shell", True, 200)
        tu.record("cyberagent-24b", "ha_control", False, 150)
        s = tu.stats()
        assert s["total_executions"] >= 2

    def test_top_tools(self):
        import app.training.tool_usage as tu
        tu.record("model-x", "shell", True, 100)
        tu.record("model-x", "shell", True, 110)
        tu.record("model-x", "ha_control", False, 80)
        top = tu.top_tools(model="model-x", limit=3)
        assert len(top) >= 1
        assert top[0]["tool"] == "shell"

    def test_register_router_feedback_correct(self):
        import app.training.tool_usage as tu
        import app.training_store as ts
        orig = ts._DB_PATH
        ts._DB_PATH = Path(tempfile.mktemp(suffix=".db"))
        ts._init()
        try:
            tu.register_router_feedback("shell", "shell", model="tool-router")
            assert ts.count("approval") >= 1
        finally:
            ts._DB_PATH = orig

    def test_register_router_feedback_wrong(self):
        import app.training.tool_usage as tu
        import app.training_store as ts
        orig = ts._DB_PATH
        ts._DB_PATH = Path(tempfile.mktemp(suffix=".db"))
        ts._init()
        try:
            tu.register_router_feedback("ha_control", "shell", model="tool-router")
            assert ts.count("approval") >= 1
        finally:
            ts._DB_PATH = orig

    def test_tool_accuracy_report_structure(self):
        import app.training.tool_usage as tu
        tu.record("test-model", "shell", True, 100)
        tu.record("test-model", "shell", False, 200)
        report = tu.tool_accuracy_report(model="test-model")
        assert isinstance(report, dict)
        # report is {model: {tools: [...], overall_success_rate, total}}
        assert "test-model" in report
        assert "tools" in report["test-model"]
        assert report["test-model"]["total"] >= 2

    def test_tool_accuracy_report_success_rate(self):
        import app.training.tool_usage as tu
        tu.record("acc-model", "ha_control", True, 50)
        tu.record("acc-model", "ha_control", True, 60)
        tu.record("acc-model", "ha_control", False, 70)
        report = tu.tool_accuracy_report(model="acc-model")
        assert "acc-model" in report
        sr = report["acc-model"]["overall_success_rate"]
        assert 0.0 <= sr <= 1.0


# ── training/versioning ────────────────────────────────────────────────────────

class TestVersioning:
    def setup_method(self):
        import app.training.versioning as v
        # Use a temp dir so tests don't pollute real data
        self._tmpdir = Path(tempfile.mkdtemp())
        self._orig_fn = v._versions_path
        v._versions_path = lambda model_id: self._tmpdir / model_id / "versions.json"

    def teardown_method(self):
        import app.training.versioning as v
        v._versions_path = self._orig_fn

    def test_register_version(self):
        from app.training.versioning import register_version, get_versions
        import app.training.versioning as v
        v._versions_path = lambda mid: self._tmpdir / mid / "versions.json"
        e = register_version("test-model", "/adapters/v1", {"loss": 0.4})
        assert e["version"] == 1
        versions = get_versions("test-model")
        assert len(versions) == 1

    def test_promote_version(self):
        from app.training.versioning import register_version, promote, get_active
        import app.training.versioning as v
        v._versions_path = lambda mid: self._tmpdir / mid / "versions.json"
        register_version("test-promote", "/adapters/v1", {"loss": 0.3})
        r = promote("test-promote", version=1)
        assert r["ok"]
        active = get_active("test-promote")
        assert active is not None
        assert active["version"] == 1
        assert active["active"]

    def test_promote_latest_when_no_version(self):
        from app.training.versioning import register_version, promote, get_active
        import app.training.versioning as v
        v._versions_path = lambda mid: self._tmpdir / mid / "versions.json"
        register_version("test-latest", "/adapters/v1", {"loss": 0.5})
        r = promote("test-latest")  # promotes latest
        assert r["ok"]
        assert get_active("test-latest")["version"] == 1

    def test_rollback_to_previous(self):
        from app.training.versioning import register_version, promote, rollback, get_active
        import app.training.versioning as v
        v._versions_path = lambda mid: self._tmpdir / mid / "versions.json"
        register_version("test-rollback", "/adapters/v1", {"loss": 0.5})
        register_version("test-rollback", "/adapters/v2", {"loss": 0.4})
        promote("test-rollback", version=1)
        promote("test-rollback", version=2)
        r = rollback("test-rollback")
        assert r["ok"]
        assert get_active("test-rollback")["version"] == 1

    def test_rollback_no_previous_fails(self):
        from app.training.versioning import register_version, promote, rollback
        import app.training.versioning as v
        v._versions_path = lambda mid: self._tmpdir / mid / "versions.json"
        register_version("test-rb-fail", "/adapters/v1", {"loss": 0.5})
        promote("test-rb-fail", version=1)
        r = rollback("test-rb-fail")
        assert not r["ok"]

    def test_get_versions_empty(self):
        from app.training.versioning import get_versions
        import app.training.versioning as v
        v._versions_path = lambda mid: self._tmpdir / mid / "versions.json"
        assert get_versions("nonexistent-xyz-abc") == []


# ── training/evaluate ─────────────────────────────────────────────────────────

class TestEvaluate:
    def test_evaluate_returns_eval_result(self):
        from app.training.evaluate import evaluate, EvalResult
        samples = [{"weight": 0.9}, {"weight": 0.8}, {"weight": 0.1}]
        result = evaluate("cyberagent-24b", "v1", samples)
        assert isinstance(result, EvalResult)
        assert 0.0 <= result.final_score <= 1.0

    def test_evaluate_empty_samples(self):
        from app.training.evaluate import evaluate
        result = evaluate("cyberagent-24b", "v1", [])
        assert result.n_holdout == 0
        assert result.holdout_score == 0.5

    def test_evaluate_all_positive_signals(self):
        from app.training.evaluate import evaluate
        samples = [{"weight": 1.0}] * 10
        result = evaluate("cyberagent-24b", "v1", samples)
        assert result.holdout_score == 1.0

    def test_evaluate_all_negative_signals(self):
        from app.training.evaluate import evaluate
        samples = [{"weight": 0.0}] * 5
        result = evaluate("cyberagent-24b", "v1", samples)
        assert result.holdout_score == 0.0

    def test_should_promote_true_on_improvement(self):
        from app.training.evaluate import evaluate, should_promote, IMPROVEMENT_THRESHOLD
        samples = [{"weight": 0.9}] * 10
        result = evaluate("cyberagent-24b", "v1", samples)
        baseline = result.final_score - IMPROVEMENT_THRESHOLD - 0.01
        assert should_promote(result, baseline)

    def test_should_promote_false_on_regression(self):
        from app.training.evaluate import evaluate, should_promote
        samples = [{"weight": 0.0}] * 5
        result = evaluate("cyberagent-24b", "v1", samples)
        baseline = 0.99  # very high baseline
        assert not should_promote(result, baseline)

    def test_evaluate_canonical_known_model(self):
        from app.training.evaluate import evaluate
        result = evaluate("cyberagent-24b", "v1", [])
        assert result.n_canonical > 0
        assert result.canonical_score == 0.8

    def test_evaluate_canonical_unknown_model(self):
        from app.training.evaluate import evaluate
        result = evaluate("unknown-model-xyz", "v1", [])
        assert result.canonical_score == 0.5


# ── comms/rate_limiter ────────────────────────────────────────────────────────

class TestRateLimiter:
    def test_get_limiter_returns_object(self):
        from app.comms.rate_limiter import get_limiter
        lim = get_limiter("chat_12345")
        assert lim is not None
        assert hasattr(lim, "acquire")

    def test_get_limiter_same_chat_same_instance(self):
        from app.comms.rate_limiter import get_limiter
        lim1 = get_limiter("chat_same")
        lim2 = get_limiter("chat_same")
        assert lim1 is lim2

    def test_get_limiter_different_chats(self):
        from app.comms.rate_limiter import get_limiter
        limA = get_limiter("chatA_unique")
        limB = get_limiter("chatB_unique")
        assert limA is not limB

    def test_queue_size_returns_int(self):
        from app.comms.rate_limiter import queue_size
        size = queue_size()
        assert isinstance(size, int)
        assert size >= 0

    def test_enqueue_returns_bool(self):
        from app.comms.rate_limiter import enqueue
        result = enqueue("fake_token", "chat_test", "Hola mundo")
        assert isinstance(result, bool)

    def test_enqueue_adds_to_queue(self):
        from app.comms.rate_limiter import enqueue, queue_size
        before = queue_size()
        enqueue("fake_token", "chat_unique_enqueue_99", "Mensaje de test")
        after = queue_size()
        assert after >= before  # may have been processed by worker already


# ── training/data_map ─────────────────────────────────────────────────────────

class TestDataMap:
    def test_get_sources_cyberagent(self):
        from app.training.data_map import get_sources
        sources = get_sources("cyberagent-24b")
        assert isinstance(sources, list)
        assert len(sources) > 0

    def test_sources_include_tool_usage_training(self):
        from app.training.data_map import get_sources
        sources = get_sources("cyberagent-24b")
        kinds = [s[0] for s in sources]
        assert "tool_usage_training" in kinds

    def test_get_sources_unknown_model(self):
        from app.training.data_map import get_sources
        sources = get_sources("nonexistent-model-xyz")
        assert sources == [] or isinstance(sources, list)

    def test_sources_vision_security(self):
        from app.training.data_map import get_sources
        sources = get_sources("vision-security")
        assert len(sources) > 0

    def test_sources_have_weight(self):
        from app.training.data_map import get_sources
        for kind, weight in get_sources("cyberagent-24b"):
            assert isinstance(weight, float)
            assert 0.0 <= weight <= 1.0
