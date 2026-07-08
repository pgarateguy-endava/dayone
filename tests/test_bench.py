from pathlib import Path

import pytest

import bench.db as db_mod
import bench.tools.eod_report as eod_report_mod
from bench.seed import seed
from bench.tools.catalog import create_task, load_profile, load_track
from bench.tools.eod_report import build_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.state import (
    load_bench_state,
    record_check_in,
    start_bench,
    update_task_status,
)
from bench.tools.verify_goals import verify_progress


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    monkeypatch.setattr(eod_report_mod, "REPORTS_DIR", tmp_path / "reports")
    seed()
    return tmp_path


def test_seed_loads_relational_catalog(seeded_db):
    track = load_track("aws-backend-track")
    assert track["name"] == "AWS Backend Upskilling Track"
    assert len(track["tasks"]) == 8  # one-to-many
    course = next(t for t in track["tasks"] if t["title"].startswith("AWS Cloud Practitioner"))
    assert course["follow_up"] == "twice_daily"
    assert course["contacts"][0]["name"] == "Juan Pérez"
    profile = load_profile("senior-dev")
    assert "prod-write" in profile["approvals_required"]


def test_start_bench_instantiates_person_tasks(seeded_db):
    state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    assert len(state["tasks"]) == 8
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
    assert len(state["tasks"]) == 9  # new catalog task instantiated for Ada too


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
