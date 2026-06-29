"""Unit tests for app/model_router.py — score_complexity and route."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.model_router import score_complexity, route, FAST_MODEL, POWER_MODEL


class TestScoreComplexity:
    def test_short_greeting_is_trivial(self):
        assert score_complexity("hola") == 0.0

    def test_simple_system_query_is_low(self):
        assert score_complexity("cuánta RAM tengo") < 0.3

    def test_complex_pattern_boosts_score(self):
        s = score_complexity("diseña todo el sistema de autenticación desde cero con JWT y TOTP")
        assert s >= 0.5

    def test_exploit_pattern_boosts_score(self):
        s = score_complexity("crea un exploit completo funcional para este buffer overflow")
        assert s >= 0.5

    def test_long_message_scores_higher(self):
        short = score_complexity("hola")
        long  = score_complexity(("analiza el sistema " * 30).strip())
        assert long > short

    def test_code_blocks_boost_score(self):
        msg = "lee este código:\n```python\nx = 1\n```\ny dime qué hace\n```bash\nls\n```"
        s = score_complexity(msg)
        assert s > 0.0

    def test_multiple_paragraphs_boost(self):
        msg = "Primero haz esto.\n\nDespués haz esto.\n\nPor último haz aquello también."
        s = score_complexity(msg)
        assert s > 0.0

    def test_score_clamped_to_one(self):
        very_long = ("implementa completo el sistema " * 50) + " ``` code ``` más código ```"
        s = score_complexity(very_long)
        assert 0.0 <= s <= 1.0


class TestRoute:
    """Local-first por diseño: route() NUNCA escala a la nube automáticamente.
    La nube solo se usa cuando el usuario elige un modelo cloud en el selector
    (esa ruta no pasa por route()). Ver model_router.route()."""

    def test_simple_message_stays_local(self):
        model, reason = route("hola, ¿qué tal?")
        assert model == FAST_MODEL
        assert "local" in reason.lower()

    def test_complex_message_stays_local(self):
        model, _ = route(
            "diseña todo el sistema de autenticación completo desde cero con JWT, TOTP y bcrypt"
        )
        assert model == FAST_MODEL  # no auto-escala a la nube

    def test_offensive_security_stays_local(self):
        model, _ = route("crea un exploit completo funcional para este buffer overflow")
        assert model == FAST_MODEL

    def test_threshold_ignored_always_local(self):
        assert route("hola", threshold=0.0)[0] == FAST_MODEL
        assert route("arquitectura completa desde cero", threshold=1.0)[0] == FAST_MODEL

    def test_reason_mentions_local(self):
        _, reason = route("escanear la red")
        assert "local" in reason.lower()
