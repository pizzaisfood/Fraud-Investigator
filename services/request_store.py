import json
import os
import sqlite3
from typing import Any


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "investigations.sqlite3")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investigation_requests (
                request_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                transaction_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                node_traces_json TEXT NOT NULL,
                state_json TEXT NOT NULL
            )
            """
        )


def save_request(record: dict[str, Any]) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO investigation_requests (
                request_id,
                created_at,
                status,
                transaction_json,
                result_json,
                node_traces_json,
                state_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["request_id"],
                record["created_at"],
                record.get("status", "completed"),
                json.dumps(record.get("transaction") or {}, ensure_ascii=False),
                json.dumps(record.get("result") or {}, ensure_ascii=False),
                json.dumps(record.get("node_traces") or [], ensure_ascii=False),
                json.dumps(record.get("state") or {}, ensure_ascii=False),
            ),
        )


def load_requests() -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM investigation_requests
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        {
            "request_id": row["request_id"],
            "created_at": row["created_at"],
            "status": row["status"],
            "transaction": json.loads(row["transaction_json"]),
            "result": json.loads(row["result_json"]),
            "node_traces": json.loads(row["node_traces_json"]),
            "state": json.loads(row["state_json"]),
        }
        for row in rows
    ]
