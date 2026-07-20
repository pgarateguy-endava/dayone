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


def _onboard(client, email="ada@test.com"):
    return client.post("/api/v1/onboard", json={
        "employee_name": "Ada Lovelace", "employee_email": email,
        "profile_id": "backend-dev", "track_id": "aws-backend-track"})


def test_catalog_and_onboard(client):
    cat = client.get("/api/v1/catalog").json()
    assert any(p["id"] == "senior-dev" for p in cat["profiles"])
    response = _onboard(client)
    assert response.status_code == 200
    assert "Bench plan - Ada Lovelace" in response.json()["reply"]


def test_unknown_person_is_404_with_hint(client):
    response = client.get("/api/v1/plan/nobody@test.com")
    assert response.status_code == 404
    assert "onboard" in response.json()["detail"]


def test_task_update_checkin_and_report(client):
    _onboard(client)
    response = client.post("/api/v1/task", json={
        "employee_email": "ada@test.com", "task_id": 2,
        "status": "in_progress", "evidence": "curso al 40%"})
    assert "in_progress" in response.json()["reply"]

    response = client.post("/api/v1/checkin", json={
        "employee_email": "ada@test.com", "period": "pm", "blockers": "licencia Udemy"})
    reply = response.json()["reply"]
    assert "EOD report - Ada Lovelace" in reply and "licencia Udemy" in reply

    assert "tasks done" not in client.get("/api/v1/tasks/ada@test.com").json()["reply"]
    assert "#2" in client.get("/api/v1/tasks/ada@test.com").json()["reply"]


def test_chat_falls_back_deterministically_without_llm(client):
    # In this test env langchain isn't installed, so /chat exercises the fallback:
    # keyword shortcuts + verified status. The channel never dies.
    _onboard(client)
    assert "Bench plan" in client.post("/api/v1/chat", json={
        "employee_email": "ada@test.com", "text": "plan"}).json()["reply"]
    reply = client.post("/api/v1/chat", json={
        "employee_email": "ada@test.com", "text": "como vengo con mis metas?"}).json()["reply"]
    assert "tasks done" in reply


def test_chat_fallback_marks_profile_update_done(client):
    _onboard(client)

    reply = client.post("/api/v1/chat", json={
        "employee_email": "Ada@Test.com",
        "text": "Hoy termine de preparar el profile",
    }).json()["reply"]

    assert "lo dejo registrado" in reply
    assert "planificar un bench exitoso" in reply
    tasks = client.get("/api/v1/tasks/ada@test.com").json()["reply"]
    assert "[done] Update Endava profile" in tasks


def test_chat_fallback_marks_named_mandatory_done(client):
    _onboard(client)

    reply = client.post("/api/v1/chat", json={
        "employee_email": "ada@test.com",
        "text": "hice Claude Partner Network Learning Path",
    }).json()["reply"]

    assert "Claude Partner Network Learning Path" in reply
    tasks = client.get("/api/v1/tasks/ada@test.com").json()["reply"]
    assert "[done] Claude Partner Network Learning Path" in tasks


def test_chat_fallback_planning_acceptance_starts_with_mandatory(client):
    _onboard(client)

    reply = client.post("/api/v1/chat", json={
        "employee_email": "ada@test.com",
        "text": "quiero planificar mi bench",
    }).json()["reply"]

    assert "Mandatory primero" in reply
    assert "Claude Partner Network" in reply


def test_chat_unknown_person_gets_onboarding_hint_not_404(client):
    reply = client.post("/api/v1/chat", json={
        "employee_email": "new@test.com", "text": "hola"})
    assert reply.status_code == 200
    assert "alta" in reply.json()["reply"]


def test_api_token_enforced_when_set(client, monkeypatch):
    # Unset (default) -> open: covered by every other test. Set -> bearer required.
    monkeypatch.setenv("BENCH_API_TOKEN", "s3cret")
    assert client.get("/api/v1/catalog").status_code == 401
    assert client.get(
        "/api/v1/catalog", headers={"Authorization": "Bearer nope"}).status_code == 401
    ok = client.get("/api/v1/catalog", headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200
    assert any(p["id"] == "senior-dev" for p in ok.json()["profiles"])
