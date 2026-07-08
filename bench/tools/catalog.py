"""Catalog read/write tools over the relational model. (Read + Write tools)

Replaces the YAML loaders for the Bench domain: profiles, tracks, tasks and
contacts now live in SQLite (seeded by bench/seed.py).
"""
from __future__ import annotations

from typing import Any

from bench.db import connect


def _task_dict(conn, row) -> dict[str, Any]:
    contacts = conn.execute(
        "SELECT name, email, note FROM task_contacts WHERE task_id = ?", (row["id"],)
    ).fetchall()
    task = dict(row)
    task["contacts"] = [dict(c) for c in contacts]
    return task


def load_profile(profile_id: str) -> dict[str, Any]:
    """Load a role/profile with its permissions and approval-required actions."""
    with connect() as conn:
        profile = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if profile is None:
            available = [r["id"] for r in conn.execute("SELECT id FROM profiles")]
            raise KeyError(f"Profile '{profile_id}' not found. Available: {available}")
        permissions: dict[str, list[str]] = {}
        for row in conn.execute(
                "SELECT kind, value FROM profile_permissions WHERE profile_id = ?", (profile_id,)):
            permissions.setdefault(row["kind"], []).append(row["value"])
        approvals = [r["action"] for r in conn.execute(
            "SELECT action FROM profile_approvals WHERE profile_id = ?", (profile_id,))]
    return {**dict(profile), "permissions": permissions, "approvals_required": approvals}


def load_track(track_id: str) -> dict[str, Any]:
    """Load a track with its tasks (one-to-many), contacts and responsibles."""
    with connect() as conn:
        track = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
        if track is None:
            available = [r["id"] for r in conn.execute("SELECT id FROM tracks")]
            raise KeyError(f"Track '{track_id}' not found. Available: {available}")
        tasks = [_task_dict(conn, r) for r in conn.execute(
            "SELECT * FROM tasks WHERE track_id = ? ORDER BY sort, id", (track_id,))]
        responsibles = [dict(r) for r in conn.execute(
            "SELECT name, email, role FROM responsibles WHERE track_id = ?", (track_id,))]
        profiles = [r["profile_id"] for r in conn.execute(
            "SELECT profile_id FROM track_profiles WHERE track_id = ?", (track_id,))]
    return {**dict(track), "tasks": tasks, "responsibles": responsibles,
            "target_profiles": profiles}


def list_profiles() -> list[dict[str, Any]]:
    with connect() as conn:
        return [load_profile(r["id"]) for r in conn.execute("SELECT id FROM profiles ORDER BY id")]


def list_tracks() -> list[dict[str, Any]]:
    with connect() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM tracks ORDER BY id")]
    return [load_track(t) for t in ids]


def create_task(track_id: str, title: str, description: str = "", category: str = "admin",
                due_date: str | None = None, follow_up: str = "daily",
                est_hours: float | None = None, link: str = "",
                evidence_required: bool = True, requires_approval: bool = False,
                contacts: list[dict] | None = None) -> int:
    """Add a task to a track's catalog. Returns the new task id. (Write tool)

    New tasks are also instantiated for everyone already on bench with that track.
    """
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (track_id, title, description, category, due_date, follow_up, "
            "est_hours, link, evidence_required, requires_approval, sort) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            " COALESCE((SELECT MAX(sort) + 1 FROM tasks WHERE track_id = ?), 1))",
            (track_id, title, description, category, due_date, follow_up,
             est_hours, link, int(evidence_required), int(requires_approval), track_id))
        task_id = cursor.lastrowid
        for contact in contacts or []:
            conn.execute(
                "INSERT INTO task_contacts (task_id, name, email, note) VALUES (?, ?, ?, ?)",
                (task_id, contact.get("name", ""), contact.get("email", ""),
                 contact.get("note", "")))
        conn.executemany(
            "INSERT OR IGNORE INTO person_tasks (email, task_id) VALUES (?, ?)",
            [(r["email"], task_id) for r in conn.execute(
                "SELECT email FROM people WHERE track_id = ?", (track_id,))])
    return task_id


def upsert_profile(profile_id: str, name: str, summary: str = "",
                   permissions: list[tuple[str, str]] | None = None,
                   approvals: list[str] | None = None) -> None:
    """Create or replace a role/profile with its permissions and approvals. (Write tool)"""
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO profiles (id, name, summary) VALUES (?, ?, ?)",
                     (profile_id, name, summary))
        conn.execute("DELETE FROM profile_permissions WHERE profile_id = ?", (profile_id,))
        conn.execute("DELETE FROM profile_approvals WHERE profile_id = ?", (profile_id,))
        conn.executemany(
            "INSERT INTO profile_permissions (profile_id, kind, value) VALUES (?, ?, ?)",
            [(profile_id, k, v) for k, v in permissions or []])
        conn.executemany(
            "INSERT INTO profile_approvals (profile_id, action) VALUES (?, ?)",
            [(profile_id, a) for a in approvals or []])


def add_task_contact(task_id: int, name: str, email: str = "", note: str = "") -> None:
    """Attach a reference person to a task (e.g. someone who already took the course)."""
    with connect() as conn:
        conn.execute("INSERT INTO task_contacts (task_id, name, email, note) VALUES (?, ?, ?, ?)",
                     (task_id, name, email, note))
