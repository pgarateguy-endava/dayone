from pathlib import Path

import pytest

import bench.tools.eod_report as eod_report_mod
import bench.tools.state as state_mod
from agent.tools.load_profile import load_profile
from bench.tools.eod_report import build_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.load_track import load_track
from bench.tools.verify_goals import verify_daily_goals


@pytest.fixture()
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(state_mod, "PROGRESS_DIR", tmp_path)
    monkeypatch.setattr(eod_report_mod, "REPORTS_DIR", tmp_path / "reports")
    return tmp_path


def test_bench_plan_contains_track_and_profile_data():
    profile = load_profile("backend-dev")
    track = load_track("aws-backend-track")
    plan = generate_bench_plan("Ada Lovelace", "ada@example.com", profile, track)
    assert "Ada Lovelace" in plan
    assert "AWS Backend Upskilling Track" in plan
    assert "AWS Cloud Practitioner Essentials" in plan
    assert "prod-write" in plan  # approvals come from the profile, not the track


def test_verify_goals_marks_met_and_missed(isolated_state):
    track = load_track("aws-backend-track")
    state_mod.start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    state_mod.record_check_in("ada@test.com", "am", planned=["module 2"])
    state_mod.record_check_in(
        "ada@test.com", "pm",
        done_goals=[{"goal": 1, "evidence": "course at 50%"}],
        blockers="license pending",
    )
    state = state_mod.load_bench_state("ada@test.com")
    result = verify_daily_goals(state, track)
    assert result["goals_total"] == 3
    assert result["goals_met"] == 1
    assert result["met"][0]["goal"] == 1
    assert len(result["missed"]) == 2
    assert result["blockers"] == ["license pending"]
    assert result["checked_in_am"] and result["checked_in_pm"]


def test_eod_report_renders_and_saves(isolated_state):
    track = load_track("aws-backend-track")
    state_mod.start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    state_mod.record_check_in("ada@test.com", "pm", done_goals=[{"goal": 2, "evidence": "commit abc"}])
    state = state_mod.load_bench_state("ada@test.com")
    verification = verify_daily_goals(state, track)
    report = build_eod_report(state, track, verification)
    assert "EOD report - Ada" in report
    assert "people.lead@example.com" in report
    assert "commit abc" in report
    path = eod_report_mod.save_eod_report(report, "ada@test.com", verification["date"])
    assert Path(path).exists()


def test_daily_cycle_graph_pm_produces_report(isolated_state):
    pytest.importorskip("langgraph")
    from bench.graph import build_graph

    state_mod.start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    app = build_graph()
    result = app.invoke({
        "employee_email": "ada@test.com",
        "period": "pm",
        "done_goals": [{"goal": 1, "evidence": "course at 70%"}],
        "planned": [],
        "blockers": "",
    })
    assert result["verification"]["goals_met"] == 1
    assert "EOD report" in result["report_md"]
    assert Path(result["report_path"]).exists()
    assert "people.lead@example.com" in result["notified"]
