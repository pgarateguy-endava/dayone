"""Bench state per person: assignment, task instances and check-ins. (Write/Read tools)

The catalog task is the template; `person_tasks` is the instance that carries the
STATUS for each person (pending / in_progress / done / blocked) plus evidence.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from bench.db import TASK_STATUSES, connect, normalize_email, stable_person_id


def _text_key(text: str) -> str:
    return (
        text.strip().lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
    )


def _title_matches(title: str, query: str) -> bool:
    title_key = _text_key(title)
    query_key = _text_key(query)
    if not title_key or not query_key:
        return False
    if title_key in query_key or query_key in title_key:
        return True
    tokens = [token for token in query_key.replace("-", " ").split() if len(token) > 2]
    return len(tokens) >= 3 and all(token in title_key for token in tokens)


def computed_status(bench_start_date: str | None, on_date: str | None = None) -> str:
    """Status is COMPUTED from the bench start date (single source of truth):
    no date -> inactive · future date -> pre_bench · today/past -> active."""
    if not bench_start_date:
        return "inactive"
    today = date.fromisoformat(on_date) if on_date else date.today()
    return "pre_bench" if date.fromisoformat(bench_start_date) > today else "active"


def start_bench(employee_name: str, employee_email: str, profile_id: str, track_id: str,
                bench_start_date: str | None = None,
                profile_text: str = "", profile_filename: str = "") -> dict:
    """Create (or reset) the bench record and instantiate the track's tasks. (Write tool)

    The activation status is computed from bench_start_date — see computed_status().
    profile_text: extracted Endava Profile content — the AI's context about the person.
    """
    employee_email = normalize_email(employee_email)
    status = computed_status(bench_start_date)
    with connect() as conn:
        existing = conn.execute(
            "SELECT person_id FROM people WHERE email_normalized = ?", (employee_email,)
        ).fetchone()
        person_id = existing["person_id"] if existing else stable_person_id(employee_email)
        conn.execute("DELETE FROM check_ins WHERE email = ?", (employee_email,))
        conn.execute("DELETE FROM person_tasks WHERE email = ?", (employee_email,))
        if existing:
            conn.execute(
                "UPDATE people SET name = ?, profile_id = ?, track_id = ?, started_at = ?, "
                "status = ?, bench_start_date = ?, profile_text = ?, profile_filename = ?, "
                "archived = 0 WHERE person_id = ?",
                (employee_name, profile_id, track_id, datetime.now(timezone.utc).isoformat(),
                 status, bench_start_date, profile_text, profile_filename, person_id),
            )
        else:
            conn.execute(
                "INSERT INTO people (person_id, email, email_normalized, name, profile_id, "
                "track_id, started_at, status, bench_start_date, profile_text, profile_filename) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (person_id, employee_email, employee_email, employee_name, profile_id, track_id,
                 datetime.now(timezone.utc).isoformat(), status, bench_start_date,
                 profile_text, profile_filename),
            )
        conn.executemany(
            "INSERT INTO person_tasks (person_id, email, task_id) VALUES (?, ?, ?)",
            [(person_id, employee_email, r["id"]) for r in conn.execute(
                "SELECT id FROM tasks WHERE track_id = ? ORDER BY sort, id", (track_id,))])
    return load_bench_state(employee_email)


def load_bench_state(employee_email: str) -> dict[str, Any]:
    """Load a person's bench record: profile, track, task instances, check-ins. (Read tool)"""
    employee_email = normalize_email(employee_email)
    with connect() as conn:
        person = conn.execute(
            "SELECT * FROM people WHERE email_normalized = ?", (employee_email,)).fetchone()
        if person is None:
            raise FileNotFoundError(
                f"No bench state for '{employee_email}'. Run: python -m bench.app start ...")
        tasks = [dict(r) for r in conn.execute(
            """SELECT pt.task_id, pt.status, pt.evidence, pt.progress_note,
                      pt.updated_at, pt.completed_at,
                      t.title, t.description, t.category, t.due_date, t.follow_up,
                      t.est_hours, t.link, t.evidence_required, t.requires_approval
               FROM person_tasks pt JOIN tasks t ON t.id = pt.task_id
               WHERE pt.person_id = ? ORDER BY t.sort, t.id""", (person["person_id"],))]
        check_ins = [
            {**dict(r), "planned": json.loads(r["planned"])}
            for r in conn.execute(
                "SELECT date, period, planned, blockers, note, at FROM check_ins "
                "WHERE person_id = ? ORDER BY id", (person["person_id"],))]
    return {
        "person_id": person["person_id"],
        "employee_name": person["name"],
        "employee_email": person["email"],
        "profile_id": person["profile_id"],
        "track_id": person["track_id"],
        "started_at": person["started_at"],
        "status": computed_status(person["bench_start_date"]),
        "bench_start_date": person["bench_start_date"],
        "profile_text": person["profile_text"],
        "profile_filename": person["profile_filename"],
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


def mark_profile_update_done(employee_email: str, evidence: str = "", note: str = "") -> dict:
    """Mark this person's Endava Profile update task as done. (Write tool)

    The agent should not guess task ids for this common pre-bench intent; this helper
    deterministically finds the person's `profile_update` task instance.
    """
    with connect() as conn:
        task = conn.execute(
            """SELECT pt.task_id, t.title
               FROM person_tasks pt JOIN tasks t ON t.id = pt.task_id
               WHERE pt.email = ? AND t.category = 'profile_update'
               ORDER BY t.sort, t.id
               LIMIT 1""",
            (employee_email,)).fetchone()
    if task is None:
        raise KeyError(f"No profile update task is assigned to {employee_email}")
    reported = evidence or "Person reported that the Endava Profile is ready."
    result = update_task_status(
        employee_email,
        task["task_id"],
        "done",
        reported,
        note or "Marked from the pre-bench chat.")
    return {**result, "title": task["title"]}


def _find_assigned_task_by_title(conn, employee_email: str, title_query: str):
    tasks = conn.execute(
        """SELECT pt.task_id, t.title
           FROM person_tasks pt JOIN tasks t ON t.id = pt.task_id
           WHERE pt.email = ?
           ORDER BY t.sort, t.id""",
        (employee_email,)).fetchall()
    for task in tasks:
        if _text_key(task["title"]) == _text_key(title_query):
            return task
    for task in tasks:
        if _title_matches(task["title"], title_query):
            return task
    return None


def _ensure_mandatory_task_from_knowledge(conn, employee_email: str, title_query: str):
    person = conn.execute("SELECT * FROM people WHERE email = ?", (employee_email,)).fetchone()
    if person is None:
        raise FileNotFoundError(f"No bench state for '{employee_email}'.")
    mandatory = conn.execute(
        "SELECT * FROM knowledge WHERE kind = 'mandatory_course' ORDER BY id").fetchall()
    knowledge_item = next((item for item in mandatory if _title_matches(item["title"], title_query)), None)
    if knowledge_item is None:
        return None

    task = conn.execute(
        "SELECT id, title FROM tasks WHERE track_id = ? AND lower(title) = lower(?)",
        (person["track_id"], knowledge_item["title"])).fetchone()
    if task is None:
        cursor = conn.execute(
            """INSERT INTO tasks (track_id, title, description, category, due_date, follow_up,
                                  est_hours, link, evidence_required, requires_approval, sort)
               VALUES (?, ?, ?, 'course', ?, 'daily', 2, ?, 1, 0, 0)""",
            (
                person["track_id"],
                knowledge_item["title"],
                "Mandatory Endava course for everyone on bench; register completion in Endava University.",
                person["bench_start_date"],
                knowledge_item["url"],
            ))
        task_id = cursor.lastrowid
        title = knowledge_item["title"]
    else:
        task_id = task["id"]
        title = task["title"]

    conn.execute(
        "INSERT OR IGNORE INTO person_tasks (email, task_id) VALUES (?, ?)",
        (employee_email, task_id))
    return {"task_id": task_id, "title": title}


def mark_task_done_by_title(employee_email: str, title_query: str,
                            evidence: str = "", note: str = "") -> dict:
    """Mark a named task as done without requiring the agent to know its task id. (Write tool)

    This handles natural chat like "hice Claude Partner Network Learning Path". If a
    mandatory course exists only in the knowledge grid, it is materialized into the
    person's track before being marked done.
    """
    with connect() as conn:
        task = _find_assigned_task_by_title(conn, employee_email, title_query)
        if task is None:
            task = _ensure_mandatory_task_from_knowledge(conn, employee_email, title_query)
        if task is None:
            raise KeyError(f"No assigned task matches '{title_query}' for {employee_email}")
    reported = evidence or f"Person reported completing: {title_query}"
    result = update_task_status(
        employee_email,
        task["task_id"],
        "done",
        reported,
        note or "Marked from chat by task title.")
    return {**result, "title": task["title"]}


def record_check_in(employee_email: str, period: str, planned: list[str] | None = None,
                    blockers: str = "", note: str = "") -> dict:
    """Record the AM/PM check-in journal entry. (Write tool)

    Task progress itself goes through `update_task_status`; the check-in captures
    intent (AM: planned focus) and context (blockers, notes).
    """
    if period not in ("am", "pm"):
        raise ValueError("period must be 'am' or 'pm'")
    state = load_bench_state(employee_email)  # raises if not on bench
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
            "INSERT INTO check_ins (person_id, email, date, period, planned, blockers, note, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (state["person_id"], employee_email, event["date"], event["period"],
             json.dumps(event["planned"], ensure_ascii=False),
             event["blockers"], event["note"], event["at"]))
    return event


def set_bench_start_date(employee_email: str, bench_start_date: str | None) -> None:
    """THE activation trigger: changing the date recomputes the status and clears the
    person's notification history so the proactive rules re-fire. (Write)"""
    with connect() as conn:
        conn.execute("UPDATE people SET bench_start_date = ?, status = ? WHERE email = ?",
                     (bench_start_date, computed_status(bench_start_date), employee_email))
        conn.execute("DELETE FROM notifications WHERE email = ?", (employee_email,))


def list_bench_people() -> list[dict[str, Any]]:
    """List everyone currently on bench. (Read tool — responsibles dashboard)"""
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM people ORDER BY started_at")]
