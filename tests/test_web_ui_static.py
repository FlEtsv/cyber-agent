from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# La web es un producto unico: una sola fuente de verdad en apps/web,
# consumida por el PC (server local) y por el relay (cable a la nube).
WEB = "apps/web"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_web_headers_prefer_active_model():
    source = _read(f"{WEB}/app.js")

    assert "_preferredModelLabel" in source
    assert "return activeModel ||" in source
    assert "_setHeaderModel" in source


def test_connected_event_uses_synced_active_model():
    source = _read(f"{WEB}/app.js")
    connected_block = source.split("case 'connected':", 1)[1].split("case 'models':", 1)[0]

    assert "this.activeModel = data?.active_model || '';" in connected_block
    assert "this._setHeaderModel(this.availableModels, this.activeModel);" in connected_block
    assert "data.models.find(m => m === 'cyberagent-original')" not in connected_block


def test_model_selector_does_not_keep_hidden_stale_model():
    source = _read(f"{WEB}/app.js")
    sync_block = source.split("_syncModelSelect() {", 1)[1].split("_renderPermissionsList()", 1)[0]

    assert "const normalizedModel = this.selectedModel === 'auto' ? '' : this.selectedModel;" in sync_block
    assert "this.selectedModel = '';" in sync_block
    assert "this._savePreferences();" in sync_block


def test_pc_relay_connector_passes_requested_model_to_runner():
    source = _read("app/api/relay_connector.py")
    on_message_block = source.split("async def _handle_message", 1)[1].split("async def _handle_new_session", 1)[0]

    assert "requested_model = _requested_model_from_message(msg)" in on_message_block
    assert "model            = requested_model" in on_message_block
    assert "Modelo solicitado desde relay" in on_message_block


def test_web_exposes_conversation_and_activity_shell():
    html = _read(f"{WEB}/index.html")
    js = _read(f"{WEB}/app.js")

    assert 'id="conversation-panel"' in html
    assert 'id="conversation-list"' in html
    assert 'id="activity-list"' in html
    assert "_conversationsKey" in js
    assert "_switchConversation" in js
    assert "_renderActivity" in js
    assert "content.innerHTML = renderMd(text);" in js


def test_login_uses_fixed_email_code_flow():
    html = _read(f"{WEB}/login.html")

    assert 'id="fixed-email"' in html
    assert "/api/auth/totp/verify" in html
    assert 'id="l-email"' not in html
    assert 'id="l-pass"' not in html


def test_web_is_single_product_source():
    """Garantiza que la web no se vuelve a duplicar fuera de apps/web."""
    assert not (ROOT / "app" / "web" / "static").exists(), \
        "app/web/static no debe existir: la web vive solo en apps/web"
    assert not (ROOT / "app" / "web" / "index.html").exists(), \
        "app/web/index.html no debe existir: la web vive solo en apps/web"
