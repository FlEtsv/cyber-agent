import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tool_router import route_tools
from app.tools import get_tool_meta, is_dangerous, tool_names_by_category


def _names(schema: list[dict]) -> set[str]:
    return {tool["function"]["name"] for tool in schema}


def test_mistral_consult_is_cloud_ask_high_risk():
    meta = get_tool_meta("mistral_consult")

    assert meta["category"] == "council"
    assert meta["risk"] == "high"
    assert meta["default_permission"] == "ask"
    assert meta["dangerous"] is True
    assert is_dangerous("mistral_consult") is True


def test_council_category_contains_only_external_consult_tool():
    assert tool_names_by_category("council") == {"mistral_consult"}


def test_mistral_keyword_routes_council_tool():
    routed = route_tools("pide segunda opinion a Mistral para esta auditoria", use_llm=False)

    assert "mistral_consult" in _names(routed)
