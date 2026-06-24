import json, os, tempfile, shutil
from datetime import datetime
from app import database as db

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def rate_message(message_id: int, conversation_id: int, rating: int):
    """rating: 1 = positivo, -1 = negativo"""
    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO message_ratings (message_id, conversation_id, rating)
               VALUES (?, ?, ?)
               ON CONFLICT(message_id) DO UPDATE SET rating=excluded.rating,
               created_at=datetime('now')""",
            (message_id, conversation_id, rating),
        )


def get_rating(message_id: int) -> int | None:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT rating FROM message_ratings WHERE message_id=?",
            (message_id,),
        ).fetchone()
    return row["rating"] if row else None


def export_jsonl(output_path: str = None) -> tuple[str, int]:
    if output_path is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(DATA_DIR, f"finetune_{ts}.jsonl")

    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT mr.rating, mr.message_id, mr.conversation_id
               FROM message_ratings mr
               WHERE mr.rating = 1
               ORDER BY mr.created_at""",
        ).fetchall()

    count = 0
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jsonl", dir=DATA_DIR)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            for row in rows:
                conv_msgs = db.get_messages(row["conversation_id"])
                for i, msg in enumerate(conv_msgs):
                    if msg["id"] == row["message_id"] and i > 0:
                        prev = conv_msgs[i - 1]
                        if prev["role"] == "user":
                            entry = {
                                "messages": [
                                    {"role": "user",      "content": prev["content"]},
                                    {"role": "assistant", "content": msg["content"]},
                                ]
                            }
                            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            count += 1
        shutil.move(tmp_path, output_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return output_path, count


def get_stats() -> dict:
    with db.get_conn() as conn:
        row = conn.execute(
            """SELECT
                   COUNT(*) as total,
                   SUM(CASE WHEN rating=1  THEN 1 ELSE 0 END) as positivos,
                   SUM(CASE WHEN rating=-1 THEN 1 ELSE 0 END) as negativos
               FROM message_ratings"""
        ).fetchone()
    return dict(row) if row else {"total": 0, "positivos": 0, "negativos": 0}
