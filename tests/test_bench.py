from pathlib import Path
import sqlite3

import pytest

import bench.db as db_mod
import bench.tools.eod_report as eod_report_mod
from bench.seed import seed
from bench.tools.catalog import create_task, load_profile, load_track
from bench.tools.eod_report import build_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.state import (
    load_bench_state,
    mark_task_done_by_title,
    record_check_in,
    start_bench,
    update_task_status,
)
from bench.tools.verify_goals import verify_progress


def _legacy_db(path: Path, *, duplicate_people: bool = False) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(db_mod._SCHEMA)
    conn.executemany(
        "INSERT INTO profiles (id, name) VALUES (?, ?)",
        [("backend-dev", "Backend Developer")],
    )
    conn.execute(
        "INSERT INTO tracks (id, name) VALUES (?, ?)",
        ("track", "Track"),
    )
    people = [(" Ada@Test.com ", "Ada", "backend-dev", "track", "2026-01-01")]
    if duplicate_people:
        people.append(("ada@test.com", "Ada Clone", "backend-dev", "track", "2026-01-02"))
    conn.executemany(
        "INSERT INTO people (email, name, profile_id, track_id, started_at) VALUES (?, ?, ?, ?, ?)",
        people,
    )
    conn.execute("INSERT INTO tasks (track_id, title) VALUES ('track', 'Task')")
    conn.execute("INSERT INTO person_tasks (email, task_id) VALUES (?, 1)", (" Ada@Test.com ",))
    conn.execute(
        "INSERT INTO check_ins (email, date, period, at) VALUES (?, '2026-01-01', 'am', 'now')",
        (" Ada@Test.com ",),
    )
    conn.execute(
        "INSERT INTO conversation_refs (email, conversation_id, updated_at) VALUES (?, 'conv', 'now')",
        (" Ada@Test.com ",),
    )
    conn.execute(
        "INSERT INTO notifications (email, kind, message, created_at) VALUES (?, 'kickoff', 'hello', 'now')",
        (" Ada@Test.com ",),
    )
    conn.commit()
    conn.close()


def test_legacy_schema_is_backfilled_with_durable_identity_and_history(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    _legacy_db(tmp_path / "bench.db")

    with db_mod.connect() as conn:
        person = conn.execute("SELECT * FROM people").fetchone()
        assert person["person_id"]
        assert person["email_normalized"] == "ada@test.com"
        assert person["archived"] == 0
        for table in ("person_tasks", "check_ins", "conversation_refs", "notifications"):
            row = conn.execute(f"SELECT person_id FROM {table}").fetchone()
            assert row["person_id"] == person["person_id"]
        assert conn.execute("SELECT archived FROM tasks WHERE id = 1").fetchone()[0] == 0
        versions = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        assert [row[0] for row in versions] == [1, 2, 3]


def test_migration_is_idempotent_and_preserves_stable_id(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    _legacy_db(tmp_path / "bench.db")
    with db_mod.connect() as conn:
        person_id = conn.execute("SELECT person_id FROM people").fetchone()[0]
    with db_mod.connect() as conn:
        assert conn.execute("SELECT person_id FROM people").fetchone()[0] == person_id
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 3


def test_duplicate_normalized_people_fail_before_backfill(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    _legacy_db(tmp_path / "bench.db", duplicate_people=True)

    with pytest.raises(db_mod.MigrationConflictError, match="duplicate normalized person email"):
        db_mod.connect()
    conn = sqlite3.connect(tmp_path / "bench.db")
    assert "person_id" not in {row[1] for row in conn.execute("PRAGMA table_info(people)")}
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 0
    conn.close()


def test_email_edit_keeps_person_id_and_history_attribution(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    _legacy_db(tmp_path / "bench.db")
    with db_mod.connect() as conn:
        person_id = conn.execute("SELECT person_id FROM people").fetchone()[0]

    assert db_mod.update_person_email("ada@test.com", " ADA.NEW@Test.com ") == person_id

    with db_mod.connect() as conn:
        person = conn.execute("SELECT * FROM people").fetchone()
        assert person["email"] == "ada.new@test.com"
        assert person["email_normalized"] == "ada.new@test.com"
        assert person["person_id"] == person_id
        assert conn.execute("SELECT email, person_id FROM check_ins").fetchone()[0] == "ada.new@test.com"
        assert conn.execute("SELECT person_id FROM person_tasks").fetchone()[0] == person_id


def test_case_insensitive_responsible_conflict_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    conn = sqlite3.connect(tmp_path / "bench.db")
    conn.executescript(db_mod._SCHEMA)
    conn.execute("INSERT INTO tracks (id, name) VALUES ('track', 'Track')")
    conn.executemany(
        "INSERT INTO responsibles (track_id, name, email) VALUES ('track', ?, ?)",
        [("One", "lead@example.com"), ("Two", " LEAD@example.com ")],
    )
    conn.commit()
    conn.close()

    with pytest.raises(db_mod.MigrationConflictError, match="responsible conflict"):
        db_mod.connect()


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    monkeypatch.setattr(eod_report_mod, "REPORTS_DIR", tmp_path / "reports")
    seed()
    return tmp_path


def test_seed_loads_relational_catalog(seeded_db):
    track = load_track("aws-backend-track")
    assert track["name"] == "AWS Backend Upskilling Track"
    assert len(track["tasks"]) == 9  # one-to-many
    assert track["tasks"][0]["title"] == "Claude Partner Network Learning Path"
    course = next(t for t in track["tasks"] if t["title"].startswith("AWS Cloud Practitioner"))
    assert course["follow_up"] == "twice_daily"
    assert course["contacts"][0]["name"] == "Juan Pérez"
    profile = load_profile("senior-dev")
    assert "prod-write" in profile["approvals_required"]


def test_start_bench_instantiates_person_tasks(seeded_db):
    state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    assert len(state["tasks"]) == 9
    assert all(t["status"] == "pending" for t in state["tasks"])


def test_plan_renders_tasks_contacts_and_access(seeded_db):
    start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    plan = generate_bench_plan("Ada", "ada@test.com",
                               load_profile("backend-dev"), load_track("aws-backend-track"))
    assert "AWS Cloud Practitioner Essentials" in plan
    assert "Juan Pérez" in plan
    assert "prod-write" in plan  # approvals still come from the profile


def test_verify_progress_tracks_status_and_freshness(seeded_db):
    state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    first_task = state["tasks"][0]["task_id"]
    update_task_status("ada@test.com", first_task, "in_progress", evidence="course at 50%")
    record_check_in("ada@test.com", "pm", blockers="license pending")
    state = load_bench_state("ada@test.com")
    result = verify_progress(state, load_track("aws-backend-track"))
    touched = next(f for f in result["follow_up_today"] if f["task_id"] == first_task)
    assert touched["touched_today"] and touched["evidence"] == "course at 50%"
    assert result["pending_today"] > 0  # the rest were not touched
    assert "license pending" in result["blockers"]
    assert result["tasks_done"] == 0


def test_mark_task_done_by_title_handles_mandatory_course(seeded_db):
    start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")

    result = mark_task_done_by_title(
        "ada@test.com",
        "hice Claude Partner Network Learning Path",
        evidence="reported in chat")

    assert result["title"] == "Claude Partner Network Learning Path"
    state = load_bench_state("ada@test.com")
    claude = next(t for t in state["tasks"] if t["title"] == "Claude Partner Network Learning Path")
    assert claude["status"] == "done"
    assert claude["evidence"] == "reported in chat"


def test_eod_report_renders_and_saves(seeded_db):
    state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    update_task_status("ada@test.com", state["tasks"][0]["task_id"], "done",
                       evidence="certificate url")
    state = load_bench_state("ada@test.com")
    track = load_track("aws-backend-track")
    verification = verify_progress(state, track)
    report = build_eod_report(state, track, verification)
    assert "EOD report - Ada" in report
    assert "people.lead@example.com" in report
    path = eod_report_mod.save_eod_report(report, "ada@test.com", verification["date"])
    assert Path(path).exists()


def test_create_task_backfills_people_on_bench(seeded_db):
    start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    create_task("aws-backend-track", "New security course", category="course",
                follow_up="weekly", contacts=[{"name": "Sofía", "note": "took it"}])
    state = load_bench_state("ada@test.com")
    assert len(state["tasks"]) == 10  # new catalog task instantiated for Ada too


def test_materialized_knowledge_task_keeps_durable_person_link(seeded_db):
    start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    with db_mod.connect() as conn:
        task_id = conn.execute(
            "SELECT id FROM tasks WHERE title = 'Claude Partner Network Learning Path'"
        ).fetchone()[0]
        conn.execute("DELETE FROM person_tasks WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    mark_task_done_by_title("ada@test.com", "Claude Partner Network Learning Path")

    with db_mod.connect() as conn:
        row = conn.execute(
            "SELECT pt.person_id, pt.status FROM person_tasks pt "
            "JOIN tasks t ON t.id = pt.task_id "
            "WHERE pt.email = 'ada@test.com' AND t.title = 'Claude Partner Network Learning Path'"
        ).fetchone()
        person_id = conn.execute(
            "SELECT person_id FROM people WHERE email_normalized = 'ada@test.com'"
        ).fetchone()[0]
    assert row["person_id"] == person_id
    assert row["status"] == "done"


def test_unknown_person_start_date_does_not_clear_legacy_notifications(seeded_db):
    with db_mod.connect() as conn:
        conn.execute(
            "INSERT INTO notifications (email, kind, message, created_at) "
            "VALUES ('lead@example.com', 'eod_report', 'keep', 'now')"
        )

    from bench.tools.state import set_bench_start_date
    set_bench_start_date("unknown@example.com", "2026-07-21")

    with db_mod.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE email = 'lead@example.com'"
        ).fetchone()[0] == 1


def test_daily_cycle_graph_pm_produces_report(seeded_db):
    pytest.importorskip("langgraph")
    from bench.graph import build_graph

    state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    result = build_graph().invoke({
        "employee_email": "ada@test.com",
        "period": "pm",
        "task_updates": [{"task_id": state["tasks"][0]["task_id"],
                          "status": "in_progress", "evidence": "course at 70%"}],
        "planned": [],
        "blockers": "",
    })
    assert result["verification"]["touched_today"] == 1
    assert "EOD report" in result["report_md"]
    assert Path(result["report_path"]).exists()
    assert "people.lead@example.com" in result["notified"]
