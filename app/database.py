import sqlite3, json, os, threading
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cyberagent.db")

_local = threading.local()

def get_conn():
    if not getattr(_local, "conn", None):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn

def init_db():
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
        """)

def create_conversation(title="Nueva conversación"):
    with get_conn() as c:
        cur = c.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
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
        c.execute("DELETE FROM message_ratings WHERE conversation_id=?", (conv_id,))
        c.execute("DELETE FROM decision_log WHERE conversation_id=?", (conv_id,))
        c.execute("DELETE FROM conversation_memory WHERE conversation_id=?", (conv_id,))
        c.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
        c.execute("DELETE FROM conversations WHERE id=?", (conv_id,))

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
