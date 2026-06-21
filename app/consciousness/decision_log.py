import json
from app import database as db


def log_decision(conversation_id, tool_name: str, args: dict,
                 result: dict, approved: bool):
    result_str = json.dumps(result, ensure_ascii=False)
    if len(result_str) > 4000:
        result_str = result_str[:4000] + "..."
    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO decision_log
               (conversation_id, tool_name, args_json, result_json, approved)
               VALUES (?, ?, ?, ?, ?)""",
            (
                conversation_id,
                tool_name,
                json.dumps(args, ensure_ascii=False),
                result_str,
                1 if approved else 0,
            ),
        )


def get_recent_decisions(limit: int = 50) -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM decision_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    with db.get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as total,
                      SUM(approved) as approved,
                      COUNT(*) - SUM(approved) as rejected
               FROM decision_log"""
        ).fetchone()
    return dict(row) if row else {"total": 0, "approved": 0, "rejected": 0}
