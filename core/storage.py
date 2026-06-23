"""
SQLite persistence layer for per-student misconception tracking.

The DB lives at <project_root>/lumi_data.db and is created automatically on
first import. No external dependencies — uses only stdlib sqlite3.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

_DB = Path(__file__).parent.parent / "lumi_data.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.row_factory = sqlite3.Row
    return c


def _init() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS misconceptions (
                student_id    TEXT    NOT NULL,
                misconception TEXT    NOT NULL,
                grade_group   TEXT    NOT NULL,
                seen_count    INTEGER NOT NULL DEFAULT 1,
                last_seen     TEXT    NOT NULL,
                PRIMARY KEY (student_id, misconception)
            )
        """)


_init()


def record_misconception(student_id: str, misconception: str, grade_group: str) -> None:
    """Increment the seen_count for a misconception, or insert it on first occurrence."""
    if misconception == "unknown_error":
        return
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO misconceptions (student_id, misconception, grade_group, seen_count, last_seen)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(student_id, misconception)
            DO UPDATE SET seen_count = seen_count + 1, last_seen = excluded.last_seen
            """,
            (student_id, misconception, grade_group, now),
        )


def get_student_report(student_id: str) -> list[dict]:
    """Return all misconceptions for a student, most frequent first."""
    with _conn() as c:
        rows = c.execute(
            """
            SELECT misconception, grade_group, seen_count, last_seen
            FROM misconceptions
            WHERE student_id = ?
            ORDER BY seen_count DESC, last_seen DESC
            """,
            (student_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_students() -> list[dict]:
    """Return a summary row per student for the teacher dashboard."""
    with _conn() as c:
        rows = c.execute(
            """
            SELECT student_id,
                   SUM(seen_count)               AS total_errors,
                   COUNT(DISTINCT misconception)  AS distinct_misconceptions,
                   MAX(last_seen)                 AS last_active
            FROM misconceptions
            GROUP BY student_id
            ORDER BY last_active DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]
