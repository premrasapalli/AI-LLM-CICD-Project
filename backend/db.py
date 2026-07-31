import json
import os
import sqlite3
import time

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "app.db"))


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_sha TEXT,
            branch TEXT,
            score INTEGER,
            summary TEXT,
            report TEXT,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS ci_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            name TEXT,
            status TEXT,
            conclusion TEXT,
            head_sha TEXT,
            created_at INTEGER
        );
        """
    )
    conn.commit()
    conn.close()


def save_review(commit_sha, branch, score, summary, report):
    conn = _connect()
    conn.execute(
        "INSERT INTO reviews (commit_sha, branch, score, summary, report, created_at) VALUES (?,?,?,?,?,?)",
        (commit_sha, branch, score, summary, json.dumps(report), int(time.time())),
    )
    conn.commit()
    conn.close()


def get_reviews(limit=20):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) | {"report": json.loads(r["report"])} for r in rows]


def save_ci_runs(runs):
    conn = _connect()
    for r in runs:
        conn.execute(
            "INSERT OR REPLACE INTO ci_runs (run_id, name, status, conclusion, head_sha, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (r.get("id"), r.get("name"), r.get("status"), r.get("conclusion"), r.get("head_sha"), int(time.time())),
        )
    conn.commit()
    conn.close()


def get_ci_runs(limit=20):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM ci_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
