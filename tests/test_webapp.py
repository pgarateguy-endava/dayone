import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import bench.tools.eod_report as eod_report_mod
import bench.tools.state as state_mod
from bench.webapp import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_ENABLED", "1")
    monkeypatch.setattr(state_mod, "PROGRESS_DIR", tmp_path)
    monkeypatch.setattr(eod_report_mod, "REPORTS_DIR", tmp_path / "reports")
    return TestClient(app)


def test_flag_gate_blocks_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_ENABLED", "0")
    assert TestClient(app).get("/").status_code == 403


def test_onboard_person_cycle_and_dashboard(client):
    # onboard
    response = client.post("/onboard", data={
        "employee": "Ada Lovelace", "email": "ada@test.com",
        "profile": "backend-dev", "track": "aws-backend-track",
    }, follow_redirects=False)
    assert response.status_code == 303

    # person view shows the plan and the goals
    page = client.get("/person/ada@test.com").text
    assert "Bench plan - Ada Lovelace" in page
    assert "AWS Backend Upskilling Track" in page

    # PM check-in through the LangGraph cycle
    response = client.post("/person/ada@test.com/checkin", data={
        "period": "pm", "done": ["1"], "evidence_1": "course at 40%", "blockers": "",
    }, follow_redirects=False)
    assert response.status_code == 303

    # dashboard reflects verified progress
    dash = client.get("/").text
    assert "Ada Lovelace" in dash
    assert "1/3 goals" in dash

    # EOD report renders
    assert "EOD report - Ada Lovelace" in client.get("/person/ada@test.com/report").text


def test_catalog_shows_role_track_relation(client):
    page = client.get("/catalog").text
    assert "Backend Developer" in page
    assert "aws-backend-track" in page
    assert "Needs approval:" in page
