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
            -- A4: archivos generados, asociados a carpeta/conversación.
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                name TEXT,
                url TEXT,
                folder_id INTEGER,
                conversation_id INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migración idempotente: columnas nuevas en conversations.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(conversations)")}
        if "folder_id" not in cols:
            c.execute("ALTER TABLE conversations ADD COLUMN folder_id INTEGER")
        if "color" not in cols:
            c.execute("ALTER TABLE conversations ADD COLUMN color TEXT")
        # WEBPROD-012: favoritos en files (persisten aunque se borre la conversación).
        fcols = {r["name"] for r in c.execute("PRAGMA table_info(files)")}
        if "favorite" not in fcols:
            c.execute("ALTER TABLE files ADD COLUMN favorite INTEGER DEFAULT 0")
        if "kind" not in fcols:
            c.execute("ALTER TABLE files ADD COLUMN kind TEXT")

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
            # WEBPROD-012: los favoritos se conservan (se desligan); el resto de
            # adjuntos de la conversación se eliminan con ella.
            c.execute("UPDATE files SET conversation_id=NULL "
                      "WHERE conversation_id=? AND favorite=1", (conv_id,))
            c.execute("DELETE FROM files "
                      "WHERE conversation_id=? AND (favorite IS NULL OR favorite=0)", (conv_id,))
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


def folder_context_chain(folder_id):
    """WEBPROD-010: cadena de carpetas de raíz→hoja (categoría → subcategoría),
    para heredar el contexto del padre en las subcategorías/proyectos."""
    chain = []
    seen = set()
    with get_conn() as c:
        fid = folder_id
        while fid is not None and fid not in seen and len(chain) < 6:
            seen.add(fid)
            row = c.execute("SELECT * FROM folders WHERE id=?", (fid,)).fetchone()
            if not row:
                break
            d = dict(row)
            chain.append(d)
            fid = d.get("parent_id")
    chain.reverse()  # raíz primero
    return chain


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


def register_file(path, name=None, url=None, folder_id=None, conversation_id=None, kind=None):
    """A4/WEBPROD-011: registra un archivo (generado o adjunto), asociado a una
    carpeta/conversación. Devuelve el id de la fila o None."""
    try:
        with get_conn() as c:
            cur = c.execute(
                "INSERT INTO files (path, name, url, folder_id, conversation_id, kind) "
                "VALUES (?,?,?,?,?,?)",
                (str(path), name or os.path.basename(str(path)), url,
                 folder_id, conversation_id, kind))
            return cur.lastrowid
    except Exception:
        return None


def get_files(folder_id="__all__", conversation_id="__all__", favorites_only=False):
    """Lista archivos. Filtra por carpeta y/o conversación; o solo favoritos."""
    where, params = [], []
    if favorites_only:
        where.append("favorite=1")
    if folder_id != "__all__":
        where.append("folder_id IS ?"); params.append(folder_id)
    if conversation_id != "__all__":
        where.append("conversation_id IS ?"); params.append(conversation_id)
    sql = "SELECT * FROM files"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY favorite DESC, created_at DESC LIMIT 300"
    with get_conn() as c:
        return [dict(r) for r in c.execute(sql, params)]


def set_file_favorite(file_id, favorite=True):
    """WEBPROD-012: marca/desmarca un archivo como favorito (persiste al borrar la conv)."""
    with get_conn() as c:
        c.execute("UPDATE files SET favorite=? WHERE id=?", (1 if favorite else 0, file_id))


def delete_file(file_id):
    """Elimina el registro de un archivo (no borra el fichero físico)."""
    with get_conn() as c:
        c.execute("DELETE FROM files WHERE id=?", (file_id,))


def cleanup_conversation_files(conversation_id):
    """WEBPROD-012: al borrar una conversación (incluidas las de la web en
    localStorage), conserva sus archivos favoritos (los desliga) y elimina el resto."""
    with get_conn() as c:
        c.execute("UPDATE files SET conversation_id=NULL "
                  "WHERE conversation_id IS ? AND favorite=1", (conversation_id,))
        c.execute("DELETE FROM files "
                  "WHERE conversation_id IS ? AND (favorite IS NULL OR favorite=0)",
                  (conversation_id,))


def get_conversation_folder(conv_id):
    """Devuelve la carpeta (dict) de una conversación, o None. Para inyectar
    contexto y modelo por defecto de la carpeta (A3)."""
    if conv_id is None:
        return None
    with get_conn() as c:
        row = c.execute(
            "SELECT f.* FROM folders f JOIN conversations c ON c.folder_id = f.id "
            "WHERE c.id = ?", (conv_id,)).fetchone()
        return dict(row) if row else None
