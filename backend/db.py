"""
SQLite database for keep-asking.

Schema:
  sessions  - one row per login (session_code, condition, test flag)
  linkage   - student_number ↔ session_code (destroyed on deidentify)
  turns     - every message exchanged (user, assistant_raw, assistant_display, system)
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path

_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    """Return the module-level connection (created by init_db)."""
    if _conn is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _conn


def init_db(data_dir: Path) -> sqlite3.Connection:
    """Create or open the database and ensure tables exist."""
    global _conn
    db_path = data_dir / "keep-asking.db"
    _conn = sqlite3.connect(str(db_path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA foreign_keys=ON")

    _conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_code  TEXT PRIMARY KEY,
            condition     TEXT NOT NULL CHECK (condition IN ('nudge', 'control')),
            is_test       INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS linkage (
            student_number TEXT PRIMARY KEY,
            session_code   TEXT NOT NULL REFERENCES sessions(session_code)
        );

        CREATE TABLE IF NOT EXISTS turns (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_code  TEXT NOT NULL REFERENCES sessions(session_code),
            turn_number   INTEGER NOT NULL,
            role          TEXT NOT NULL,
            content       TEXT NOT NULL,
            timestamp     TEXT NOT NULL,
            epoch         REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_code);
    """)
    _conn.commit()
    return _conn


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session(session_code: str, condition: str, is_test: bool) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (session_code, condition, is_test, created_at) VALUES (?, ?, ?, ?)",
        (session_code, condition, int(is_test), datetime.utcnow().isoformat()),
    )
    conn.commit()


def get_session(session_code: str) -> dict | None:
    row = get_conn().execute(
        "SELECT session_code, condition, is_test, created_at FROM sessions WHERE session_code = ?",
        (session_code,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_sessions() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.session_code, s.condition, s.is_test, s.created_at,
               COALESCE(MAX(t.turn_number), 0) AS turn_count
        FROM sessions s
        LEFT JOIN turns t ON t.session_code = s.session_code AND t.role = 'user'
        GROUP BY s.session_code
    """).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Linkage helpers
# ---------------------------------------------------------------------------

def get_session_code_for_student(student_number: str) -> str | None:
    row = get_conn().execute(
        "SELECT session_code FROM linkage WHERE student_number = ?",
        (student_number,),
    ).fetchone()
    return row["session_code"] if row else None


def create_linkage(student_number: str, session_code: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO linkage (student_number, session_code) VALUES (?, ?)",
        (student_number, session_code),
    )
    conn.commit()



# ---------------------------------------------------------------------------
# Turn helpers
# ---------------------------------------------------------------------------

def log_turn(session_code: str, role: str, content: str, turn_number: int) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO turns (session_code, turn_number, role, content, timestamp, epoch) VALUES (?, ?, ?, ?, ?, ?)",
        (session_code, turn_number, role, content, datetime.utcnow().isoformat(), time.time()),
    )
    conn.commit()


def get_display_history(session_code: str) -> list[dict]:
    """Return user + assistant_display turns in order (for restoring chat)."""
    rows = get_conn().execute(
        "SELECT role, content FROM turns WHERE session_code = ? AND role IN ('user', 'assistant_display') ORDER BY id",
        (session_code,),
    ).fetchall()
    result = []
    for r in rows:
        role = "assistant" if r["role"] == "assistant_display" else "user"
        result.append({"role": role, "content": r["content"]})
    return result


def get_full_transcript(session_code: str) -> list[dict]:
    """Return all turns for export."""
    rows = get_conn().execute(
        "SELECT session_code, turn_number, role, content, timestamp, epoch FROM turns WHERE session_code = ? ORDER BY id",
        (session_code,),
    ).fetchall()
    return [dict(r) for r in rows]
