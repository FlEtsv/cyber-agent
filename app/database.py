import sqlite3, json, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cyberagent.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as c:
        c.executescript("""
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
        c.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
        c.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
