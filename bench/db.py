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
import uuid
from datetime import datetime, timezone

from bench.config import PROGRESS_DIR

FOLLOW_UP_OPTIONS = ("twice_daily", "daily", "weekly", "biweekly")
TASK_CATEGORIES = ("course", "certification", "profile_update", "portfolio", "admin")
TASK_STATUSES = ("pending", "in_progress", "done", "blocked")

_MIGRATION_VERSIONS = (1, 2, 3, 4)
_PERSON_NAMESPACE = uuid.UUID("5a2c48ef-3c3c-4b0b-bf2d-6f1f6ea6b9a8")


class MigrationConflictError(RuntimeError):
    """Raised when legacy data cannot be backfilled without guessing."""

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

def normalize_email(email: str) -> str:
    """Return the canonical email key used by the Bench API and migrations."""
    return email.strip().lower()


def stable_person_id(email: str) -> str:
    """Generate the same durable identity for the same legacy person key."""
    return str(uuid.uuid5(_PERSON_NAMESPACE, f"person:{normalize_email(email)}"))


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn: sqlite3.Connection, table: str, definition: str) -> None:
    name = definition.split()[0]
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _validate_backfill_conflicts(conn: sqlite3.Connection) -> None:
    duplicate_people = conn.execute(
        "SELECT lower(trim(email)) AS normalized, COUNT(*) AS count "
        "FROM people GROUP BY lower(trim(email)) HAVING COUNT(*) > 1"
    ).fetchall()
    if duplicate_people:
        values = ", ".join(row[0] for row in duplicate_people)
        raise MigrationConflictError(
            f"duplicate normalized person email(s): {values}; resolve them before migrating"
        )

    duplicate_responsibles = conn.execute(
        "SELECT track_id, lower(trim(email)) AS normalized, COUNT(*) AS count "
        "FROM responsibles GROUP BY track_id, lower(trim(email)) HAVING COUNT(*) > 1"
    ).fetchall()
    if duplicate_responsibles:
        values = ", ".join(f"{row[0]}:{row[1]}" for row in duplicate_responsibles)
        raise MigrationConflictError(
            f"case-insensitive responsible conflict(s): {values}; resolve them before migrating"
        )


def _migration_1(conn: sqlite3.Connection) -> None:
    """Track and complete the columns previously added ad hoc at connect time."""
    _add_column(conn, "people", "status TEXT NOT NULL DEFAULT 'active'")
    _add_column(conn, "people", "bench_start_date TEXT")
    _add_column(conn, "people", "profile_text TEXT NOT NULL DEFAULT ''")
    _add_column(conn, "people", "profile_filename TEXT NOT NULL DEFAULT ''")


def _migration_2(conn: sqlite3.Connection) -> None:
    """Add durable person identity links without deleting legacy email columns."""
    _add_column(conn, "people", "person_id TEXT")
    _add_column(conn, "people", "email_normalized TEXT")
    for table in ("person_tasks", "check_ins", "conversation_refs", "notifications"):
        _add_column(conn, table, "person_id TEXT")

    for person in conn.execute("SELECT email FROM people").fetchall():
        email = person[0]
        conn.execute(
            "UPDATE people SET person_id = ?, email_normalized = ? WHERE email = ?",
            (stable_person_id(email), normalize_email(email), email),
        )

    for table in ("person_tasks", "check_ins", "conversation_refs", "notifications"):
        conn.execute(
            f"UPDATE {table} SET person_id = ("
            "SELECT p.person_id FROM people p "
            f"WHERE p.email_normalized = lower(trim({table}.email))"
            f") WHERE person_id IS NULL"
        )

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS people_person_id_idx ON people(person_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS people_email_normalized_idx "
        "ON people(email_normalized)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS person_tasks_person_id_idx ON person_tasks(person_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS check_ins_person_id_idx ON check_ins(person_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS conversation_refs_person_id_idx "
        "ON conversation_refs(person_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS notifications_person_id_idx ON notifications(person_id)"
    )


def _migration_3(conn: sqlite3.Connection) -> None:
    """Separate archive state from derived date status and preserve active defaults."""
    _add_column(conn, "people", "archived INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "tasks", "archived INTEGER NOT NULL DEFAULT 0")


def _require_person_links(conn: sqlite3.Connection, table: str) -> None:
    missing = conn.execute(
        f"SELECT 1 FROM {table} child "
        "WHERE child.person_id IS NULL OR NOT EXISTS ("
        "SELECT 1 FROM people p WHERE p.person_id = child.person_id"
        ") LIMIT 1"
    ).fetchone()
    if missing:
        raise MigrationConflictError(
            f"unattributed {table} row; resolve its person email before migrating"
        )


def _migration_4(conn: sqlite3.Connection) -> None:
    """Make durable identity required and remove historical email ownership."""
    _require_person_links(conn, "person_tasks")
    _require_person_links(conn, "check_ins")

    # Stage person-owned tables without foreign keys to the old people table so
    # people can be rebuilt with NOT NULL/check constraints in the same transaction.
    conn.execute(
        """CREATE TABLE person_tasks_stage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT,
            email TEXT NOT NULL,
            task_id INTEGER NOT NULL REFERENCES tasks(id),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','in_progress','done','blocked')),
            evidence TEXT NOT NULL DEFAULT '',
            progress_note TEXT NOT NULL DEFAULT '',
            updated_at TEXT,
            completed_at TEXT,
            UNIQUE (person_id, task_id)
        )"""
    )
    conn.execute(
        """INSERT INTO person_tasks_stage
            (id, person_id, email, task_id, status, evidence, progress_note,
             updated_at, completed_at)
            SELECT id, person_id, email, task_id, status, evidence, progress_note,
                   updated_at, completed_at
            FROM person_tasks"""
    )
    conn.execute(
        """UPDATE person_tasks_stage
           SET email = (SELECT email_normalized FROM people p
                         WHERE p.person_id = person_tasks_stage.person_id)"""
    )

    conn.execute(
        """CREATE TABLE check_ins_stage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT,
            email TEXT NOT NULL,
            date TEXT NOT NULL,
            period TEXT NOT NULL CHECK (period IN ('am', 'pm')),
            planned TEXT NOT NULL DEFAULT '[]',
            blockers TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """INSERT INTO check_ins_stage
            (id, person_id, email, date, period, planned, blockers, note, at)
            SELECT id, person_id, email, date, period, planned, blockers, note, at
            FROM check_ins"""
    )
    conn.execute(
        """UPDATE check_ins_stage
           SET email = (SELECT email_normalized FROM people p
                         WHERE p.person_id = check_ins_stage.person_id)"""
    )

    conn.execute(
        """CREATE TABLE conversation_refs_stage (
            email TEXT PRIMARY KEY,
            person_id TEXT,
            conversation_id TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """INSERT INTO conversation_refs_stage
            (email, person_id, conversation_id, updated_at)
            SELECT email, person_id, conversation_id, updated_at
            FROM conversation_refs"""
    )
    conn.execute(
        """CREATE TABLE notifications_stage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            person_id TEXT,
            kind TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            delivered_at TEXT
        )"""
    )
    conn.execute(
        """INSERT INTO notifications_stage
            (id, email, person_id, kind, message, created_at, delivered_at)
            SELECT id, email, person_id, kind, message, created_at, delivered_at
            FROM notifications"""
    )

    for table in ("person_tasks", "check_ins", "conversation_refs", "notifications"):
        conn.execute(f"DROP TABLE {table}")
    conn.execute("ALTER TABLE person_tasks_stage RENAME TO person_tasks")
    conn.execute("ALTER TABLE check_ins_stage RENAME TO check_ins")
    conn.execute("ALTER TABLE conversation_refs_stage RENAME TO conversation_refs")
    conn.execute("ALTER TABLE notifications_stage RENAME TO notifications")

    conn.execute(
        """CREATE TABLE people_stage (
            email TEXT PRIMARY KEY,
            person_id TEXT NOT NULL UNIQUE CHECK (length(trim(person_id)) > 0),
            email_normalized TEXT NOT NULL UNIQUE
                CHECK (email_normalized = lower(trim(email))),
            name TEXT NOT NULL,
            profile_id TEXT NOT NULL REFERENCES profiles(id),
            track_id TEXT NOT NULL REFERENCES tracks(id),
            started_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            bench_start_date TEXT,
            profile_text TEXT NOT NULL DEFAULT '',
            profile_filename TEXT NOT NULL DEFAULT '',
            archived INTEGER NOT NULL DEFAULT 0
        )"""
    )
    conn.execute(
        """INSERT INTO people_stage
            (email, person_id, email_normalized, name, profile_id, track_id,
             started_at, status, bench_start_date, profile_text, profile_filename, archived)
            SELECT email_normalized, person_id, email_normalized, name, profile_id, track_id,
                   started_at, status, bench_start_date, profile_text, profile_filename, archived
            FROM people"""
    )
    conn.execute("DROP TABLE people")
    conn.execute("ALTER TABLE people_stage RENAME TO people")

    conn.execute(
        """CREATE TABLE person_tasks_final (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL REFERENCES people(person_id),
            email TEXT NOT NULL,
            task_id INTEGER NOT NULL REFERENCES tasks(id),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','in_progress','done','blocked')),
            evidence TEXT NOT NULL DEFAULT '',
            progress_note TEXT NOT NULL DEFAULT '',
            updated_at TEXT,
            completed_at TEXT,
            UNIQUE (person_id, task_id)
        )"""
    )
    conn.execute(
        """INSERT INTO person_tasks_final
            (id, person_id, email, task_id, status, evidence, progress_note,
             updated_at, completed_at)
            SELECT id, person_id, email, task_id, status, evidence, progress_note,
                   updated_at, completed_at
            FROM person_tasks"""
    )
    conn.execute("DROP TABLE person_tasks")
    conn.execute("ALTER TABLE person_tasks_final RENAME TO person_tasks")

    conn.execute(
        """CREATE TABLE check_ins_final (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL REFERENCES people(person_id),
            email TEXT NOT NULL,
            date TEXT NOT NULL,
            period TEXT NOT NULL CHECK (period IN ('am', 'pm')),
            planned TEXT NOT NULL DEFAULT '[]',
            blockers TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """INSERT INTO check_ins_final
            (id, person_id, email, date, period, planned, blockers, note, at)
            SELECT id, person_id, email, date, period, planned, blockers, note, at
            FROM check_ins"""
    )
    conn.execute("DROP TABLE check_ins")
    conn.execute("ALTER TABLE check_ins_final RENAME TO check_ins")

    conn.execute(
        """CREATE TABLE conversation_refs_final (
            email TEXT PRIMARY KEY,
            person_id TEXT REFERENCES people(person_id),
            conversation_id TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """INSERT INTO conversation_refs_final
            (email, person_id, conversation_id, updated_at)
            SELECT email, person_id, conversation_id, updated_at
            FROM conversation_refs"""
    )
    conn.execute("DROP TABLE conversation_refs")
    conn.execute("ALTER TABLE conversation_refs_final RENAME TO conversation_refs")

    conn.execute(
        """CREATE TABLE notifications_final (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            person_id TEXT REFERENCES people(person_id),
            kind TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            delivered_at TEXT
        )"""
    )
    conn.execute(
        """INSERT INTO notifications_final
            (id, email, person_id, kind, message, created_at, delivered_at)
            SELECT id, email, person_id, kind, message, created_at, delivered_at
            FROM notifications"""
    )
    conn.execute("DROP TABLE notifications")
    conn.execute("ALTER TABLE notifications_final RENAME TO notifications")
    conn.execute(
        "CREATE INDEX person_tasks_person_id_idx ON person_tasks(person_id)"
    )
    conn.execute("CREATE INDEX check_ins_person_id_idx ON check_ins(person_id)")
    conn.execute(
        "CREATE INDEX conversation_refs_person_id_idx ON conversation_refs(person_id)"
    )
    conn.execute("CREATE INDEX notifications_person_id_idx ON notifications(person_id)")


def _run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    _validate_backfill_conflicts(conn)
    migrations = {1: _migration_1, 2: _migration_2, 3: _migration_3, 4: _migration_4}
    for version in _MIGRATION_VERSIONS:
        if version in applied:
            continue
        with conn:
            migrations[version](conn)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(timezone.utc).isoformat()),
            )
    violation = conn.execute("PRAGMA foreign_key_check").fetchone()
    if violation is not None:
        raise sqlite3.IntegrityError(f"foreign-key check failed: {tuple(violation)}")


def connect() -> sqlite3.Connection:
    """Open the bench DB, creating the schema if needed.

    PROGRESS_DIR is imported at module level but read here at call time,
    so tests can monkeypatch `bench.db.PROGRESS_DIR`.
    """
    PROGRESS_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(PROGRESS_DIR / "bench.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(_SCHEMA)
        _run_migrations(conn)
    except Exception:
        conn.close()
        raise
    return conn


def update_person_email(old_email: str, new_email: str) -> str:
    """Change a person's email while retaining identity and historical links."""
    old_key = normalize_email(old_email)
    new_key = normalize_email(new_email)
    if not new_key:
        raise ValueError("email must not be empty")
    with connect() as conn:
        person = conn.execute(
            "SELECT person_id FROM people WHERE email_normalized = ?", (old_key,)
        ).fetchone()
        if person is None:
            raise KeyError(f"No person for '{old_email}'")
        conflict = conn.execute(
            "SELECT 1 FROM people WHERE email_normalized = ? AND person_id != ?",
            (new_key, person[0]),
        ).fetchone()
        if conflict:
            raise MigrationConflictError(f"email already belongs to another person: {new_key}")
        conversation_conflict = conn.execute(
            "SELECT 1 FROM conversation_refs "
            "WHERE lower(trim(email)) = ? AND (person_id IS NULL OR person_id != ?)",
            (new_key, person[0]),
        ).fetchone()
        if conversation_conflict:
            raise MigrationConflictError(
                f"email conflicts with an existing conversation reference: {new_key}"
            )
        with conn:
            conn.execute(
                "UPDATE people SET email = ?, email_normalized = ? WHERE person_id = ?",
                (new_key, new_key, person[0]),
            )
            for table in ("person_tasks", "check_ins", "conversation_refs", "notifications"):
                conn.execute(
                    f"UPDATE {table} SET email = ? WHERE person_id = ?",
                    (new_key, person[0]),
                )
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise sqlite3.IntegrityError("foreign-key check failed after email update")
    return person[0]
