"""M-02: tests adicionales del módulo de seguridad + comms + training (v2)."""
from __future__ import annotations


# ── Zonas: punto en polígono / prioridad por riesgo ───────────────────────────
class TestZones:
    def test_point_in_polygon(self):
        from app.security.zones import _point_in_polygon
        sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
        assert _point_in_polygon(5, 5, sq) is True
        assert _point_in_polygon(15, 5, sq) is False
        assert _point_in_polygon(-1, -1, sq) is False


# ── Comms: niveles y plantillas ───────────────────────────────────────────────
class TestCommsLevels:
    def test_severity_order(self):
        from app.comms.levels import Severity
        assert Severity.CRITICA > Severity.ALTA > Severity.MEDIA > Severity.BAJA > Severity.PERIODICA

    def test_templates_render(self):
        from app.comms import templates as t
        r = t.render("threat_exterior", "hombre merodeando", "Exterior", "02:14", "WARNING")
        assert r["level"] == int(t.Severity.CRITICA)
        assert r["keyboard"] == "threat_exterior"
        assert "AMENAZA" in r["title"]

    def test_template_model_ready(self):
        from app.comms import templates as t
        r = t.render("model_ready", "cyberagent-24b", 1500, 1500)
        assert "cyberagent-24b" in r["body"]

    def test_template_digest(self):
        from app.comms import templates as t
        r = t.render("digest", "Resumen", ["a", "b"])
        assert "• a" in r["body"] and "• b" in r["body"]

    def test_register_override(self):
        from app.comms import templates as t
        t.register("_tmp", lambda: {"title": "X", "body": "", "level": 3,
                                    "source": "test", "emoji": "🔔", "keyboard": None})
        assert t.render("_tmp")["title"] == "X"


# ── Visión: router de métricas ────────────────────────────────────────────────
class TestVisionMetrics:
    def test_metrics_record(self, monkeypatch):
        monkeypatch.setenv("CYBERAGENT_SECURITY_ENABLED", "0")
        from app.security import vision_router as v
        before = v.metrics()["total"]
        v.route("x", "test")
        after = v.metrics()
        assert after["total"] == before + 1
        assert after["disabled"] >= 1
        assert "local_pct" in after


# ── Training: umbral ajustable ────────────────────────────────────────────────
class TestThresholdsOverride:
    def test_override_and_reset(self):
        from app.training.thresholds import set_threshold, effective, reset
        assert effective("model-x", 500) == 500
        set_threshold("model-x", 42)
        assert effective("model-x", 500) == 42
        reset("model-x")
        assert effective("model-x", 500) == 500

    def test_invalid_threshold(self):
        from app.training.thresholds import set_threshold
        assert set_threshold("m", 0)["ok"] is False


# ── Training store: excluir muestras ──────────────────────────────────────────
class TestDatasetEditor:
    def test_list_and_exclude(self):
        import app.training_store as ts
        sid = ts.record("feedback", "instr-test-xyz", "resp-test-xyz", 1.0)
        rows = ts.list_samples(kind="feedback", limit=50)
        assert any(r["id"] == sid for r in rows)
        res = ts.set_excluded(sid, True)
        assert res["ok"] and res["excluded"] is True
        rows2 = ts.list_samples(kind="feedback", limit=50, include_excluded=False)
        assert all(r["id"] != sid for r in rows2)


# ── Vault: cifrado + máscara ──────────────────────────────────────────────────
class TestVault:
    def test_set_get_mask(self):
        from app import secrets_vault as v
        v.set_secret("TEST_KEY_M02", "supersecreto123")
        assert v.get_secret("TEST_KEY_M02") == "supersecreto123"
        masked = {s["name"]: s for s in v.list_secrets_masked()}
        assert "TEST_KEY_M02" in masked
        assert "supersecreto123" not in masked["TEST_KEY_M02"]["masked"]
        v.delete_secret("TEST_KEY_M02")
        assert v.get_secret("TEST_KEY_M02") is None

    def test_reveal_requires_totp(self):
        from app import secrets_vault as v
        r = v.reveal_all("000000")
        assert r["ok"] is False


# ── Re-ID: similitud coseno ───────────────────────────────────────────────────
class TestReID:
    def test_cosine(self):
        from app.security.reid import _cosine
        assert abs(_cosine([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-6
        assert abs(_cosine([1, 0], [0, 1])) < 1e-6
