"""Unit tests for app/tool_router.py — keyword fallback and route_tools API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tool_router import (
    _ALWAYS,
    _keyword_route,
    route_tools,
    CATEGORIES,
)
from app.tools import TOOLS_SCHEMA


_ALL_TOOL_NAMES = {t["function"]["name"] for t in TOOLS_SCHEMA}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _names(schema: list) -> set:
    return {t["function"]["name"] for t in schema}


# ── _ALWAYS always included ───────────────────────────────────────────────────

class TestAlwaysTools:
    def test_always_subset_of_schema(self):
        assert _ALWAYS <= _ALL_TOOL_NAMES

    def test_route_always_includes_core(self):
        result = route_tools("buscar archivos python", use_llm=False)
        names = _names(result)
        assert _ALWAYS <= names

    def test_no_match_returns_full_schema(self):
        result = route_tools("fjkqlmxyz completamente desconocido", use_llm=False)
        names = _names(result)
        assert names == _ALL_TOOL_NAMES


# ── Keyword routing ───────────────────────────────────────────────────────────

class TestKeywordRoute:
    def test_web_keywords(self):
        for kw in ("buscar en internet", "fetch http url", "ssl certificado"):
            result = _keyword_route(kw, None, None)
            assert result is not None, f"failed for: {kw}"
            assert "web_search" in result or "ssl_info" in result or "web_fetch" in result

    def test_files_keywords(self):
        result = _keyword_route("buscar archivos .py con grep", None, None)
        assert result is not None
        assert "search_files" in result or "grep_files" in result

    def test_system_keywords(self):
        result = _keyword_route("cuánta ram tiene el sistema", None, None)
        assert result is not None
        assert "memory_info" in result or "system_info" in result

    def test_network_keywords(self):
        result = _keyword_route("escanear puertos del host 192.168.1.1", None, None)
        assert result is not None
        assert "port_scan" in result

    def test_hacking_keywords(self):
        result = _keyword_route("pentest completo a mi servidor", None, None)
        assert result is not None
        assert "port_scan" in result
        assert "web_search" in result or "ssl_info" in result

    def test_forensics_keywords(self):
        result = _keyword_route("analizar malware exe con strings y hex", None, None)
        assert result is not None
        assert "strings_extract" in result
        assert "hex_dump" in result

    def test_encode_keywords(self):
        result = _keyword_route("decodificar base64 este texto", None, None)
        assert result is not None
        assert "encode_decode" in result

    def test_desktop_keywords(self):
        result = _keyword_route("captura pantalla y haz click en el botón", None, None)
        assert result is not None
        assert "screenshot_pc" in result
        assert "click_screen" in result

    def test_rag_keywords(self):
        result = _keyword_route("recuerda este conocimiento para el futuro", None, None)
        assert result is not None
        assert "rag_add" in result or "rag_search" in result

    def test_self_keywords(self):
        result = _keyword_route("reinicia el agente ahora mismo", None, None)
        assert result is not None
        assert "restart_self" in result

    def test_unknown_returns_none(self):
        result = _keyword_route("fjkqlmxyz", None, None)
        assert result is None

    def test_history_contributes_to_match(self):
        history = [{"role": "user", "content": "necesito escanear la red"}]
        result = _keyword_route("sigue adelante", history, None)
        assert result is not None
        assert "port_scan" in result

    def test_called_tools_expand_category(self):
        result = _keyword_route("continúa", None, {"port_scan"})
        assert result is not None
        assert "port_scan" in result
        assert "dns_lookup" in result  # same "network" category


# ── route_tools public API (no LLM) ──────────────────────────────────────────

class TestRouteTools:
    def test_always_in_result(self):
        result = route_tools("escanear puertos", use_llm=False)
        names = _names(result)
        assert _ALWAYS <= names

    def test_network_message_returns_subset(self):
        result = route_tools("escanear puertos del host", use_llm=False)
        names = _names(result)
        assert "port_scan" in names
        assert len(names) < len(_ALL_TOOL_NAMES), "should return a subset, not full schema"

    def test_desktop_message(self):
        result = route_tools("haz una captura de pantalla", use_llm=False)
        names = _names(result)
        assert "screenshot_pc" in names

    def test_all_returned_tools_are_valid(self):
        for msg in [
            "busca en google",
            "lista procesos del sistema",
            "haz un pentest",
            "analiza este binario",
            "decodifica este jwt",
        ]:
            result = route_tools(msg, use_llm=False)
            for tool in result:
                assert tool["function"]["name"] in _ALL_TOOL_NAMES

    def test_called_tools_param_expands(self):
        result = route_tools(
            "continúa con el análisis", use_llm=False,
            called_tools={"hex_dump"},
        )
        names = _names(result)
        assert "hex_dump" in names
        assert "strings_extract" in names  # same forensics category

    def test_hacking_superset_of_network(self):
        net_result  = set(_names(route_tools("escanear puertos", use_llm=False)))
        hack_result = set(_names(route_tools("hacer pentest completo", use_llm=False)))
        # hacking should include at least everything network does
        assert net_result & CATEGORIES["network"] <= hack_result
