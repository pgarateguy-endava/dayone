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
    assert "Ada Lovelace" in dash and "0/9 done" in dash
    assert "EOD report - Ada Lovelace" in client.get("/person/ada@test.com/report").text


def test_review_by_employee_tree_replaces_tracks_in_nav(client):
    client.post("/onboard", data={
        "employee": "Ada Lovelace", "email": "ada@test.com",
        "profile": "backend-dev", "track": "aws-backend-track",
    }, follow_redirects=False)
    client.post("/person/ada@test.com/task/5", data={
        "status": "done", "evidence": "Profile updated",
    }, follow_redirects=False)

    page = client.get("/review?email=ada@test.com").text

    assert '<a href="/review">Review</a>' in page
    assert '<a href="/tracks">Tracks</a>' not in page
    assert "Task tree" in page
    assert "Endava Profile" in page
    assert "profile_update" not in page
    assert "Workshop - LABS" in page
    assert "Update Endava profile" in page
    assert "Profile updated" in page
    assert "Open editable board" in page


def test_roles_abm_create_edit_delete(client):
    page = client.get("/roles").text
    assert "Senior Developer" in page  # seeded senior-dev role

    # create
    response = client.post("/roles", data={
        "profile_id": "senior-qa", "name": "Senior QA", "summary": "QA leads on bench",
        "permissions": "aws: staging-read\nci_cd: view-build-logs",
        "approvals": "prod-access",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert "Senior QA" in client.get("/roles").text

    # inline edit fragment + save
    assert "senior-qa" in client.get("/roles/senior-qa/edit").text
    saved = client.post("/roles/senior-qa", data={
        "name": "Senior QA Lead", "summary": "Updated", "permissions": "aws: staging-read",
        "approvals": "",
    }).text
    assert "Senior QA Lead" in saved

    # delete unused role → empty fragment removes the row
    assert client.post("/roles/senior-qa/delete").text == ""


def test_tracks_abm_task_inline_edit_and_delete(client):
    page = client.get("/tracks").text
    assert "AWS Backend Upskilling Track" in page and "9 tasks" in page

    detail = client.get("/tracks/aws-backend-track").text
    assert "Juan Pérez" in detail and "Add task" in detail

    # add task
    response = client.post("/tracks/aws-backend-track/tasks", data={
        "title": "Security fundamentals", "description": "Internal course",
        "category": "course", "due_date": "2026-09-01", "follow_up": "weekly",
        "est_hours": "4", "contact_name": "Sofía Ruiz", "contact_note": "took it last year",
    }, follow_redirects=False)
    assert response.status_code == 303
    detail = client.get("/tracks/aws-backend-track").text
    assert "Security fundamentals" in detail and "Sofía Ruiz" in detail

    # inline edit + save (task 1 seeded)
    assert 'name="title"' in client.get("/tasks/1/edit").text
    saved = client.post("/tasks/1", data={
        "title": "AWS CP Essentials (v2)", "description": "Updated", "category": "course",
        "due_date": "2026-07-30", "follow_up": "daily", "est_hours": "12",
        "link": "", "contact_name": "Juan Pérez", "contact_note": "mentor",
    }).text
    assert "AWS CP Essentials (v2)" in saved

    # delete
    assert client.post("/tasks/1/delete").text == ""
    assert "AWS CP Essentials (v2)" not in client.get("/tracks/aws-backend-track").text


def test_knowledge_abm_edit_inline(client):
    page = client.get("/knowledge").text
    assert "Claude Partner Network Learning Path" in page
    assert 'name="title"' in client.get("/knowledge/1/edit").text
    saved = client.post("/knowledge/1", data={
        "title": "Claude Partner Path (v2)", "provider": "Anthropic",
        "url": "https://anthropic.skilljar.com/x", "register_url": "", "tags": "", "notes": "",
    }).text
    assert "Claude Partner Path (v2)" in saved
    assert client.post("/knowledge/1/delete").text == ""


def test_delete_role_in_use_is_refused(client):
    client.post("/onboard", data={
        "employee": "Ada", "email": "ada@test.com",
        "profile": "backend-dev", "track": "aws-backend-track"}, follow_redirects=False)
    refused = client.post("/roles/backend-dev/delete").text
    assert "assigned" in refused  # row comes back with the error badge
