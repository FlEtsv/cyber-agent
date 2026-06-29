import sqlite3, json, os, shutil, threading, logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger("database")

DB_PATH    = os.path.join(os.path.dirname(__file__), "..", "cyberagent.db")
_DB_PATH   = Path(DB_PATH).resolve()
_BACKUP_DIR = _DB_PATH.parent / "backups"

_local = threading.local()

def get_conn():
    if not getattr(_local, "conn", None):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn

def check_integrity() -> tuple[bool, list[str]]:
    """Run PRAGMA integrity_check on the DB. Returns (ok, messages)."""
    try:
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        conn.close()
        messages = [r[0] for r in rows]
        return (messages == ["ok"]), messages
    except Exception as exc:
        return False, [str(exc)]


def backup_db() -> Path | None:
    """Copy DB to data/backups/cyberagent_YYYYMMDD.db. Keeps last 7 daily backups."""
    if not _DB_PATH.exists():
        return None
    try:
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        dest = _BACKUP_DIR / f"cyberagent_{datetime.now().strftime('%Y%m%d')}.db"
        if not dest.exists():
            shutil.copy2(_DB_PATH, dest)
        # Prune old backups: keep latest 7
        for old in sorted(_BACKUP_DIR.glob("cyberagent_*.db"))[:-7]:
            old.unlink(missing_ok=True)
        return dest
    except Exception as exc:
        log.warning(f"DB backup failed: {exc}")
        return None


def init_db():
    ok, msgs = check_integrity()
    if not ok:
        log.error(f"[DB] integrity_check FAILED: {msgs}")
    with get_conn() as c:
        c.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT DEFAULT 'Nueva conversación',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_data TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS decision_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                tool_name TEXT NOT NULL,
                args_json TEXT,
                result_json TEXT,
                approved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS message_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL UNIQUE,
                conversation_id INTEGER,
                rating INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS conversation_memory (
                conversation_id INTEGER PRIMARY KEY,
                summary TEXT NOT NULL DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now'))
            );
            -- A1: carpetas / categorías (workspace). parent_id => subcategorías.
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                color TEXT,
                context TEXT DEFAULT '',
                default_model TEXT,
                position INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migración idempotente: columnas nuevas en conversations.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(conversations)")}
        if "folder_id" not in cols:
            c.execute("ALTER TABLE conversations ADD COLUMN folder_id INTEGER")
        if "color" not in cols:
            c.execute("ALTER TABLE conversations ADD COLUMN color TEXT")

def create_conversation(title="Nueva conversación", folder_id=None):
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO conversations (title, folder_id) VALUES (?,?)",
            (title, folder_id))
        return cur.lastrowid

def update_title(conv_id, title):
    with get_conn() as c:
        c.execute("UPDATE conversations SET title=?, updated_at=datetime('now') WHERE id=?",
                  (title[:80], conv_id))

def get_conversations():
    with get_conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT 100")]

def get_messages(conv_id):
    with get_conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (conv_id,))]

def save_message(conv_id, role, content, tool_data=None):
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO messages (conversation_id, role, content, tool_data) VALUES (?,?,?,?)",
            (conv_id, role, content, json.dumps(tool_data) if tool_data else None))
        return cur.lastrowid

def delete_conversation(conv_id):
    with get_conn() as c:
        c.execute("BEGIN")
        try:
            c.execute("DELETE FROM message_ratings WHERE conversation_id=?", (conv_id,))
            c.execute("DELETE FROM decision_log WHERE conversation_id=?", (conv_id,))
            c.execute("DELETE FROM conversation_memory WHERE conversation_id=?", (conv_id,))
            c.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
            c.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise

def get_memory_summary(conv_id):
    with get_conn() as c:
        row = c.execute(
            "SELECT summary FROM conversation_memory WHERE conversation_id=?",
            (conv_id,),
        ).fetchone()
        return row["summary"] if row else ""

def save_memory_summary(conv_id, summary):
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO conversation_memory (conversation_id, summary, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(conversation_id) DO UPDATE SET
                summary=excluded.summary,
                updated_at=datetime('now')
            """,
            (conv_id, summary),
        )


# ── A1: Carpetas / categorías (workspace) ────────────────────────────────────
_FOLDER_FIELDS = {"name", "parent_id", "color", "context", "default_model", "position"}


def create_folder(name, parent_id=None, color=None, context="", default_model=None):
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO folders (name, parent_id, color, context, default_model) "
            "VALUES (?,?,?,?,?)",
            (name.strip()[:120], parent_id, color, context or "", default_model))
        return cur.lastrowid


def get_folders():
    with get_conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM folders ORDER BY position, name")]


def get_folder(folder_id):
    with get_conn() as c:
        row = c.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
        return dict(row) if row else None


def update_folder(folder_id, **fields):
    fields = {k: v for k, v in fields.items() if k in _FOLDER_FIELDS}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with get_conn() as c:
        c.execute(f"UPDATE folders SET {sets} WHERE id=?",
                  (*fields.values(), folder_id))


def delete_folder(folder_id):
    """Borra la carpeta. Sus conversaciones y subcarpetas quedan al nivel del padre
    (no se borran datos del usuario)."""
    with get_conn() as c:
        c.execute("BEGIN")
        try:
            row = c.execute("SELECT parent_id FROM folders WHERE id=?", (folder_id,)).fetchone()
            parent = row["parent_id"] if row else None
            c.execute("UPDATE conversations SET folder_id=? WHERE folder_id=?", (parent, folder_id))
            c.execute("UPDATE folders SET parent_id=? WHERE parent_id=?", (parent, folder_id))
            c.execute("DELETE FROM folders WHERE id=?", (folder_id,))
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise


def move_conversation(conv_id, folder_id):
    with get_conn() as c:
        c.execute("UPDATE conversations SET folder_id=?, updated_at=datetime('now') WHERE id=?",
                  (folder_id, conv_id))


def set_conversation_color(conv_id, color):
    with get_conn() as c:
        c.execute("UPDATE conversations SET color=? WHERE id=?", (color, conv_id))
