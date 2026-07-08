import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import bench.db as db_mod
import bench.tools.eod_report as eod_report_mod
from bench.seed import seed
from bench.webapp import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_ENABLED", "1")
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    monkeypatch.setattr(eod_report_mod, "REPORTS_DIR", tmp_path / "reports")
    seed()
    return TestClient(app)


def test_flag_gate_blocks_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_ENABLED", "0")
    assert TestClient(app).get("/").status_code == 403


def test_onboard_task_update_and_dashboard(client):
    response = client.post("/onboard", data={
        "employee": "Ada Lovelace", "email": "ada@test.com",
        "profile": "backend-dev", "track": "aws-backend-track",
    }, follow_redirects=False)
    assert response.status_code == 303

    page = client.get("/person/ada@test.com").text
    assert "AWS Cloud Practitioner Essentials" in page
    assert "Juan Pérez" in page  # task contact rendered

    # update a task from the UI (status lives in person_tasks)
    task_id = 1
    response = client.post(f"/person/ada@test.com/task/{task_id}", data={
        "status": "in_progress", "evidence": "course at 40%",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "course at 40%" in client.get("/person/ada@test.com").text

    # PM check-in through the LangGraph cycle, then dashboard reflects it
    client.post("/person/ada@test.com/checkin", data={"period": "pm", "blockers": ""},
                follow_redirects=False)
    dash = client.get("/").text
    assert "Ada Lovelace" in dash and "0/8 done" in dash
    assert "EOD report - Ada Lovelace" in client.get("/person/ada@test.com/report").text


def test_catalog_add_task_and_role(client):
    page = client.get("/catalog").text
    assert "Senior Developer" in page  # seeded senior-dev role
    assert "AWS Backend Upskilling Track" in page

    response = client.post("/catalog/track/aws-backend-track/task", data={
        "title": "Security fundamentals", "description": "Internal course",
        "category": "course", "due_date": "2026-09-01", "follow_up": "weekly",
        "est_hours": "4", "contact_name": "Sofía Ruiz", "contact_note": "took it last year",
    }, follow_redirects=False)
    assert response.status_code == 303
    page = client.get("/catalog").text
    assert "Security fundamentals" in page and "Sofía Ruiz" in page

    response = client.post("/catalog/profile", data={
        "profile_id": "senior-qa", "name": "Senior QA", "summary": "QA leads on bench",
        "permissions": "aws: staging-read\nci_cd: view-build-logs",
        "approvals": "prod-access",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "Senior QA" in client.get("/catalog").text
