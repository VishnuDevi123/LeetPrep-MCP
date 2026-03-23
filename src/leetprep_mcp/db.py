"""
sqlite data layer for local leetcode prep tracking.

the db has two main tables:
- problems: static metadata for each saved leetcode question
- progress: time-ordered activity events (attempted/solved/reviewing/etc.)
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

# keep the db inside the project so local development stays self-contained.
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.path.join(DB_DIR, "app_database.db")
# allowed status vocabulary used by progress events.
VALID_STATUSES = {"solved", "attempted", "not_started", "reviewing", "skipped"}


def _connect() -> sqlite3.Connection:
    """open a sqlite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_status(status: str) -> str:
    """coerce human input into canonical status form and validate it."""
    normalized = status.strip().lower().replace(" ", "_")
    if normalized not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Expected one of: {sorted(VALID_STATUSES)}"
        )
    return normalized


def init_db() -> None:
    """create data directory, tables, and indexes if they do not exist yet."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leetcode_id INTEGER UNIQUE,
                title TEXT,
                slug TEXT,
                difficulty TEXT,
                patterns TEXT,
                companies TEXT,
                created_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leetcode_id INTEGER,
                status TEXT,
                time_taken_mins INTEGER,
                notes TEXT,
                created_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_progress_leetcode_id_created_at
            ON progress (leetcode_id, created_at)
            """
        )


def add_problem(
    leetcode_id: int,
    title: str,
    slug: str,
    difficulty: str,
    patterns: str,
    companies: str,
    created_at: str,
) -> dict[str, str]:
    """
    insert a problem record once.

    uses `INSERT OR IGNORE` so repeated saves for the same leetcode_id stay idempotent.
    """
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO problems
            (leetcode_id, title, slug, difficulty, patterns, companies, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (leetcode_id, title, slug, difficulty, patterns, companies, created_at),
        )
        rows_affected = cursor.rowcount

    if rows_affected > 0:
        return {"message": "Problem added successfully."}
    return {"message": "Problem already exists."}


def track_progress(
    leetcode_id: int, status: str, time_taken_mins: int, notes: str
) -> dict[str, Any]:
    """
    append one progress event for a problem.

    design note:
    this keeps full history (multiple rows per problem) instead of overwriting status,
    so analytics can answer "what changed over time?".
    """
    normalized_status = _normalize_status(status)
    # negative or missing time is clamped to zero.
    normalized_time = max(0, int(time_taken_mins or 0))
    # store timezone-aware iso timestamp for stable ordering and auditability.
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO progress (leetcode_id, status, time_taken_mins, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (leetcode_id, normalized_status, normalized_time, notes, created_at),
        )
    return {"success": True, "message": f"Progress tracked for problem {leetcode_id}"}


def get_stats_overview() -> dict[str, Any]:
    """
    compute high-level analytics from local tables.

    returns totals + "latest status" metrics + solved average time + 7-day activity.
    """
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM problems")
        total_problems = int(cursor.fetchone()["total"])

        cursor.execute("SELECT COUNT(DISTINCT leetcode_id) AS total FROM progress")
        unique_problems = int(cursor.fetchone()["total"])

        # get the latest progress row per problem id, then aggregate by status.
        cursor.execute(
            """
            WITH latest AS (
              SELECT p.leetcode_id, p.status
              FROM progress p
              INNER JOIN (
                SELECT leetcode_id, MAX(id) AS latest_id
                FROM progress
                GROUP BY leetcode_id
              ) mx
              ON p.id = mx.latest_id
            )
            SELECT
              SUM(CASE WHEN status = 'solved' THEN 1 ELSE 0 END) AS solved,
              SUM(CASE WHEN status = 'attempted' THEN 1 ELSE 0 END) AS attempted
            FROM latest
            """
        )
        row = cursor.fetchone()
        solved = int((row["solved"] or 0))
        attempted = int((row["attempted"] or 0))

        cursor.execute(
            """
            SELECT AVG(time_taken_mins) AS avg_time
            FROM progress
            WHERE status = 'solved' AND time_taken_mins > 0
            """
        )
        avg_time = float(cursor.fetchone()["avg_time"] or 0.0)

        # quick activity signal used for short-term momentum tracking.
        cursor.execute(
            """
            SELECT COUNT(*) AS recent_count
            FROM progress
            WHERE datetime(created_at) >= datetime('now', '-7 day')
            """
        )
        recent_7d = int(cursor.fetchone()["recent_count"])

    return {
        "total_problems": total_problems,
        "unique_problems_tracked": unique_problems,
        "solved_problems_latest_status": solved,
        "attempted_problems_latest_status": attempted,
        "avg_time_mins_for_solved": round(avg_time, 1),
        "activity_events_last_7_days": recent_7d,
    }


def get_problem_history(leetcode_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """
    return newest progress events with optional filtering by a single problem id.

    limit is constrained to 1..200 to avoid accidental heavy queries.
    """
    normalized_limit = max(1, min(int(limit), 200))
    query = """
        SELECT
            p.id,
            p.leetcode_id,
            pr.title,
            pr.slug,
            p.status,
            p.time_taken_mins,
            p.notes,
            p.created_at
        FROM progress p
        LEFT JOIN problems pr ON pr.leetcode_id = p.leetcode_id
    """

    # build sql conditionally so one function supports global or per-problem history.
    params: tuple[Any, ...] = ()
    if leetcode_id is not None:
        query += " WHERE p.leetcode_id = ?"
        params = (leetcode_id,)

    query += " ORDER BY p.created_at DESC, p.id DESC LIMIT ?"
    params += (normalized_limit,)

    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [dict(row) for row in rows]


def get_stats() -> dict[str, Any]:
    """legacy compact stats shape kept for compatibility with older callers."""
    overview = get_stats_overview()
    return {
        "total_solved": overview["solved_problems_latest_status"],
        "total_attempted": overview["attempted_problems_latest_status"],
        "avg_time_mins": overview["avg_time_mins_for_solved"],
        "unique_problems": overview["unique_problems_tracked"],
    }


if __name__ == "__main__":
    init_db()
