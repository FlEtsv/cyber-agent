"""WEBPROD-011/012 — adjuntos por conversación y favoritos persistentes."""
from pathlib import Path


def _fresh_db(tmp_path, monkeypatch):
    import app.database as db
    p = tmp_path / "t.db"
    monkeypatch.setattr(db, "DB_PATH", str(p))
    monkeypatch.setattr(db, "_DB_PATH", Path(p))
    db.init_db()
    return db


def test_favorites_survive_conversation_cleanup(tmp_path, monkeypatch):
    db = _fresh_db(tmp_path, monkeypatch)
    fav = db.register_file("/x/a1.txt", name="a1", conversation_id="chatA", kind="attachment")
    db.register_file("/x/a2.txt", name="a2", conversation_id="chatA", kind="attachment")
    db.register_file("/x/b1.txt", name="b1", conversation_id="chatB", kind="attachment")
    db.set_file_favorite(fav, True)

    assert {f["name"] for f in db.get_files(conversation_id="chatA")} == {"a1", "a2"}

    db.cleanup_conversation_files("chatA")
    names = {f["name"] for f in db.get_files()}
    assert "a1" in names           # favorito conservado
    assert "a2" not in names       # no-favorito eliminado
    assert "b1" in names           # otra conversación intacta

    a1 = next(f for f in db.get_files() if f["name"] == "a1")
    assert a1["conversation_id"] is None       # desligado de la conversación
    assert [f["name"] for f in db.get_files(favorites_only=True)] == ["a1"]


def test_register_file_returns_id_and_kind(tmp_path, monkeypatch):
    db = _fresh_db(tmp_path, monkeypatch)
    fid = db.register_file("/x/s.py", name="s.py", conversation_id="c1", kind="attachment")
    assert isinstance(fid, int)
    rows = db.get_files(conversation_id="c1")
    assert rows and rows[0]["kind"] == "attachment"
