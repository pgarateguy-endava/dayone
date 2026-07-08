"""Local bench state on SQLite. (Write/Read tools)

Dev storage: a single `.local-progress/bench.db` file using stdlib sqlite3 (no new deps).
The public API is storage-agnostic on purpose: in production these functions become
DynamoDB reads/writes keyed by employee email, without touching callers
(CLI, LangGraph nodes, Strands tools, web UI).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from typing import Any

from bench.config import PROGRESS_DIR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    email TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    track_id TEXT NOT NULL,
    started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS check_ins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL REFERENCES people(email),
    date TEXT NOT NULL,
    period TEXT NOT NULL CHECK (period IN ('am', 'pm')),
    done_goals TEXT NOT NULL DEFAULT '[]',
    planned TEXT NOT NULL DEFAULT '[]',
    blockers TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    # PROGRESS_DIR is read at call time so tests can monkeypatch it.
    PROGRESS_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(PROGRESS_DIR / "bench.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _check_in_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "date": row["date"],
        "period": row["period"],
        "done_goals": json.loads(row["done_goals"]),
        "planned": json.loads(row["planned"]),
        "blockers": row["blockers"],
        "note": row["note"],
        "at": row["at"],
    }


def start_bench(employee_name: str, employee_email: str, profile_id: str, track_id: str) -> dict:
    """Create (or reset) the bench state record for a person. (Write tool)"""
    with _connect() as conn:
        conn.execute("DELETE FROM check_ins WHERE email = ?", (employee_email,))
        conn.execute(
            "INSERT OR REPLACE INTO people (email, name, profile_id, track_id, started_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (employee_email, employee_name, profile_id, track_id,
             datetime.now(timezone.utc).isoformat()),
        )
    return load_bench_state(employee_email)


def load_bench_state(employee_email: str) -> dict[str, Any]:
    """Load the bench state for a person. (Read tool)"""
    with _connect() as conn:
        person = conn.execute(
            "SELECT * FROM people WHERE email = ?", (employee_email,)
        ).fetchone()
        if person is None:
            raise FileNotFoundError(
                f"No bench state for '{employee_email}'. Run: python -m bench.app start ..."
            )
        rows = conn.execute(
            "SELECT * FROM check_ins WHERE email = ? ORDER BY id", (employee_email,)
        ).fetchall()
    return {
        "employee_name": person["name"],
        "employee_email": person["email"],
        "profile_id": person["profile_id"],
        "track_id": person["track_id"],
        "started_at": person["started_at"],
        "check_ins": [_check_in_dict(r) for r in rows],
    }


def record_check_in(
    employee_email: str,
    period: str,
    done_goals: list[dict] | None = None,
    planned: list[str] | None = None,
    blockers: str = "",
    note: str = "",
) -> dict:
    """Record an AM or PM check-in. (Write tool)

    - period: "am" (declare today's focus) or "pm" (declare completions with evidence).
    - done_goals: list of {"goal": <1-based index into track daily_goals>, "evidence": str}.
    """
    if period not in ("am", "pm"):
        raise ValueError("period must be 'am' or 'pm'")
    load_bench_state(employee_email)  # raises if the person is not on bench
    event = {
        "date": date.today().isoformat(),
        "period": period,
        "done_goals": done_goals or [],
        "planned": planned or [],
        "blockers": blockers,
        "note": note,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    with _connect() as conn:
        conn.execute(
            "INSERT INTO check_ins (email, date, period, done_goals, planned, blockers, note, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (employee_email, event["date"], event["period"],
             json.dumps(event["done_goals"], ensure_ascii=False),
             json.dumps(event["planned"], ensure_ascii=False),
             event["blockers"], event["note"], event["at"]),
        )
    return event


def list_bench_people() -> list[dict[str, Any]]:
    """List everyone currently on bench. (Read tool — used by the responsibles dashboard)"""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM people ORDER BY started_at").fetchall()
    return [dict(r) for r in rows]
