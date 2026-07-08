"""Bench state per person: assignment, task instances and check-ins. (Write/Read tools)

The catalog task is the template; `person_tasks` is the instance that carries the
STATUS for each person (pending / in_progress / done / blocked) plus evidence.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from bench.db import TASK_STATUSES, connect


def start_bench(employee_name: str, employee_email: str, profile_id: str, track_id: str) -> dict:
    """Create (or reset) the bench record and instantiate the track's tasks. (Write tool)"""
    with connect() as conn:
        conn.execute("DELETE FROM check_ins WHERE email = ?", (employee_email,))
        conn.execute("DELETE FROM person_tasks WHERE email = ?", (employee_email,))
        conn.execute(
            "INSERT OR REPLACE INTO people (email, name, profile_id, track_id, started_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (employee_email, employee_name, profile_id, track_id,
             datetime.now(timezone.utc).isoformat()))
        conn.executemany(
            "INSERT INTO person_tasks (email, task_id) VALUES (?, ?)",
            [(employee_email, r["id"]) for r in conn.execute(
                "SELECT id FROM tasks WHERE track_id = ? ORDER BY sort, id", (track_id,))])
    return load_bench_state(employee_email)


def load_bench_state(employee_email: str) -> dict[str, Any]:
    """Load a person's bench record: profile, track, task instances, check-ins. (Read tool)"""
    with connect() as conn:
        person = conn.execute(
            "SELECT * FROM people WHERE email = ?", (employee_email,)).fetchone()
        if person is None:
            raise FileNotFoundError(
                f"No bench state for '{employee_email}'. Run: python -m bench.app start ...")
        tasks = [dict(r) for r in conn.execute(
            """SELECT pt.task_id, pt.status, pt.evidence, pt.progress_note,
                      pt.updated_at, pt.completed_at,
                      t.title, t.description, t.category, t.due_date, t.follow_up,
                      t.est_hours, t.link, t.evidence_required, t.requires_approval
               FROM person_tasks pt JOIN tasks t ON t.id = pt.task_id
               WHERE pt.email = ? ORDER BY t.sort, t.id""", (employee_email,))]
        check_ins = [
            {**dict(r), "planned": json.loads(r["planned"])}
            for r in conn.execute(
                "SELECT date, period, planned, blockers, note, at FROM check_ins "
                "WHERE email = ? ORDER BY id", (employee_email,))]
    return {
        "employee_name": person["name"],
        "employee_email": person["email"],
        "profile_id": person["profile_id"],
        "track_id": person["track_id"],
        "started_at": person["started_at"],
        "tasks": tasks,
        "check_ins": check_ins,
    }


def update_task_status(employee_email: str, task_id: int, status: str,
                       evidence: str = "", note: str = "") -> dict:
    """Update a person's task instance: status + evidence + note. (Write tool)

    Status is set by the person (or the UI/agent on their behalf); the verification
    tool then checks freshness and evidence — the LLM never flips statuses itself.
    """
    if status not in TASK_STATUSES:
        raise ValueError(f"status must be one of {TASK_STATUSES}")
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        updated = conn.execute(
            "UPDATE person_tasks SET status = ?, "
            "evidence = CASE WHEN ? != '' THEN ? ELSE evidence END, "
            "progress_note = CASE WHEN ? != '' THEN ? ELSE progress_note END, "
            "updated_at = ?, "
            "completed_at = CASE WHEN ? = 'done' THEN ? ELSE NULL END "
            "WHERE email = ? AND task_id = ?",
            (status, evidence, evidence, note, note, now, status, now,
             employee_email, task_id)).rowcount
        if not updated:
            raise KeyError(f"Task {task_id} is not assigned to {employee_email}")
    return {"task_id": task_id, "status": status, "evidence": evidence,
            "note": note, "updated_at": now}


def record_check_in(employee_email: str, period: str, planned: list[str] | None = None,
                    blockers: str = "", note: str = "") -> dict:
    """Record the AM/PM check-in journal entry. (Write tool)

    Task progress itself goes through `update_task_status`; the check-in captures
    intent (AM: planned focus) and context (blockers, notes).
    """
    if period not in ("am", "pm"):
        raise ValueError("period must be 'am' or 'pm'")
    load_bench_state(employee_email)  # raises if not on bench
    event = {
        "date": date.today().isoformat(),
        "period": period,
        "planned": planned or [],
        "blockers": blockers,
        "note": note,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    with connect() as conn:
        conn.execute(
            "INSERT INTO check_ins (email, date, period, planned, blockers, note, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (employee_email, event["date"], event["period"],
             json.dumps(event["planned"], ensure_ascii=False),
             event["blockers"], event["note"], event["at"]))
    return event


def list_bench_people() -> list[dict[str, Any]]:
    """List everyone currently on bench. (Read tool — responsibles dashboard)"""
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM people ORDER BY started_at")]
