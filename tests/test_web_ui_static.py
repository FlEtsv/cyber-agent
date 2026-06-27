from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_web_headers_prefer_active_model():
    for relative in ("app/web/static/app.js", "relay/web/app.js"):
        source = _read(relative)

        assert "_preferredModelLabel" in source
        assert "return activeModel ||" in source
        assert "_setHeaderModel" in source


def test_relay_connected_event_uses_synced_active_model():
    source = _read("relay/web/app.js")
    connected_block = source.split("case 'connected':", 1)[1].split("case 'models':", 1)[0]

    assert "this.activeModel = data?.active_model || '';" in connected_block
    assert "this._setHeaderModel(this.availableModels, this.activeModel);" in connected_block
    assert "data.models.find(m => m === 'cyberagent-original')" not in connected_block


def test_relay_exposes_conversation_and_activity_shell():
    html = _read("relay/web/index.html")
    js = _read("relay/web/app.js")

    assert 'id="conversation-panel"' in html
    assert 'id="conversation-list"' in html
    assert 'id="activity-list"' in html
    assert "_conversationsKey" in js
    assert "_switchConversation" in js
    assert "_renderActivity" in js
    assert "content.innerHTML = renderMd(text);" in js
