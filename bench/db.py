"""SQLite database for the Bench domain (dev storage).

Single file `.local-progress/bench.db`, stdlib sqlite3. Relational model:

    profiles 1--N profile_permissions / profile_approvals
    tracks   N--M profiles (track_profiles)         # which roles a track fits
    tracks   1--N tasks 1--N task_contacts          # the catalog (templates)
    tracks   1--N responsibles                      # who receives the EOD report
    people   1--N person_tasks (status per person)  # instances of catalog tasks
    people   1--N check_ins                         # AM/PM journal

Catalog data (profiles, tracks, tasks) is seeded by `bench/seed.py`.
In production this schema maps to DynamoDB tables / a relational store; the
functions in bench/tools keep the same signatures either way.
"""
from __future__ import annotations

import sqlite3

from bench.config import PROGRESS_DIR

FOLLOW_UP_OPTIONS = ("twice_daily", "daily", "weekly", "biweekly")
TASK_CATEGORIES = ("course", "certification", "profile_update", "portfolio", "admin")
TASK_STATUSES = ("pending", "in_progress", "done", "blocked")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS profile_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL REFERENCES profiles(id),
    kind TEXT NOT NULL,              -- aws | ci_cd | repositories
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profile_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL REFERENCES profiles(id),
    action TEXT NOT NULL             -- actions that need human approval
);
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    duration_weeks INTEGER NOT NULL DEFAULT 4
);
CREATE TABLE IF NOT EXISTS track_profiles (
    track_id TEXT NOT NULL REFERENCES tracks(id),
    profile_id TEXT NOT NULL REFERENCES profiles(id),
    PRIMARY KEY (track_id, profile_id)
);
CREATE TABLE IF NOT EXISTS responsibles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id TEXT NOT NULL REFERENCES tracks(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'people-lead'
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id TEXT NOT NULL REFERENCES tracks(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'admin'
        CHECK (category IN ('course','certification','profile_update','portfolio','admin')),
    due_date TEXT,                   -- deadline, ISO date, nullable
    follow_up TEXT NOT NULL DEFAULT 'daily'
        CHECK (follow_up IN ('twice_daily','daily','weekly','biweekly')),
    est_hours REAL,
    link TEXT NOT NULL DEFAULT '',
    evidence_required INTEGER NOT NULL DEFAULT 1,
    requires_approval INTEGER NOT NULL DEFAULT 0,
    sort INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS task_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''    -- e.g. "already took this course"
);
CREATE TABLE IF NOT EXISTS people (
    email TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    profile_id TEXT NOT NULL REFERENCES profiles(id),
    track_id TEXT NOT NULL REFERENCES tracks(id),
    started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS person_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL REFERENCES people(email),
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','in_progress','done','blocked')),
    evidence TEXT NOT NULL DEFAULT '',
    progress_note TEXT NOT NULL DEFAULT '',
    updated_at TEXT,
    completed_at TEXT,
    UNIQUE (email, task_id)
);
CREATE TABLE IF NOT EXISTS check_ins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL REFERENCES people(email),
    date TEXT NOT NULL,
    period TEXT NOT NULL CHECK (period IN ('am', 'pm')),
    planned TEXT NOT NULL DEFAULT '[]',
    blockers TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('mandatory_course','certification','course')),
    title TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    register_url TEXT NOT NULL DEFAULT '',   -- where completion must be registered
    tags TEXT NOT NULL DEFAULT '',           -- csv, matched against profile text (aws,azure,ai...)
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS conversation_refs (
    email TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (       -- daily proactive-contact log
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    kind TEXT NOT NULL,                          -- pre_bench_greeting | planning_prompt | kickoff | progress_check | eod_report
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    delivered_at TEXT
);
"""

# columns added after the first release — applied idempotently on connect
_MIGRATIONS = [
    "ALTER TABLE people ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
    "ALTER TABLE people ADD COLUMN bench_start_date TEXT",
    "ALTER TABLE people ADD COLUMN profile_text TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE people ADD COLUMN profile_filename TEXT NOT NULL DEFAULT ''",
]


def connect() -> sqlite3.Connection:
    """Open the bench DB, creating the schema if needed.

    PROGRESS_DIR is imported at module level but read here at call time,
    so tests can monkeypatch `bench.db.PROGRESS_DIR`.
    """
    PROGRESS_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(PROGRESS_DIR / "bench.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    for migration in _MIGRATIONS:
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:  # column already exists
            pass
    return conn
