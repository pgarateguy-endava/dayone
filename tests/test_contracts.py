from __future__ import annotations

import ast

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import bench.db as db_mod
import bench.app as cli_mod
import bench.tools.eod_report as eod_report_mod
from bench.tools.contracts import DomainError, execute, require_email
from bench.seed import seed
from bench.webapp import app
from bench.tools.state import load_bench_state
from bench.tools.catalog import add_responsible


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCH_ENABLED", "1")
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    monkeypatch.setattr(eod_report_mod, "REPORTS_DIR", tmp_path / "reports")
    seed()
    return TestClient(app)


def test_execute_returns_serializable_result_and_stable_expected_error():
    result = execute("example", lambda: {"person_id": "p-1"})

    assert result.operation == "example"
    assert result.as_dict() == {"operation": "example", "data": {"person_id": "p-1"}}

    with pytest.raises(DomainError) as caught:
        execute("load_person", lambda: (_ for _ in ()).throw(KeyError("missing")))
    assert caught.value.code == "not_found"


def test_email_contract_normalizes_and_rejects_empty_or_invalid_values():
    assert require_email(" Ada@Test.COM ") == "ada@test.com"
    with pytest.raises(DomainError) as caught:
        require_email(" ")
    assert caught.value.code == "validation"

    with pytest.raises(DomainError) as caught:
        require_email("not-an-email")
    assert caught.value.details == {"field": "email"}

    for malformed in ("@", "a@", "@example.com", "a b@example.com", "a/example.com"):
        with pytest.raises(DomainError):
            require_email(malformed)


def test_domain_result_rejects_backend_objects():
    with pytest.raises(TypeError):
        execute("bad_projection", lambda: object())


def test_api_maps_domain_errors_without_sqlite_exception_text(client):
    response = client.post("/api/v1/task", json={
        "employee_email": "unknown@test.com", "task_id": 1,
        "status": "in_progress",
    })

    assert response.status_code == 404
    assert "onboard" in response.json()["detail"]

    invalid = client.post("/api/v1/task", json={
        "employee_email": "not-an-email", "task_id": 1,
        "status": "in_progress",
    })
    assert invalid.status_code == 400


def test_responsible_email_uses_shared_normalization(client):
    add_responsible("aws-backend-track", "Lead", " Lead@Example.COM ")
    with db_mod.connect() as conn:
        row = conn.execute(
            "SELECT email FROM responsibles WHERE name = 'Lead' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row["email"] == "lead@example.com"


def test_cli_domain_errors_are_safe_and_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(cli_mod, "require_bench_enabled", lambda: None)
    monkeypatch.setattr(cli_mod, "seed_if_empty", lambda: None)
    monkeypatch.setattr(cli_mod.sys, "argv", ["bench.app", "plan", "--email", "not-an-email"])

    with pytest.raises(SystemExit) as raised:
        cli_mod.main()

    assert raised.value.code == 2
    assert "valid address" in capsys.readouterr().err


def test_web_and_api_person_operations_share_committed_facts(client):
    api_response = client.post("/api/v1/onboard", json={
        "employee_name": "API Person", "employee_email": "api@test.com",
        "profile_id": "backend-dev", "track_id": "aws-backend-track",
    })
    assert api_response.status_code == 200

    web_response = client.post("/onboard", data={
        "employee": "Web Person", "email": "web@test.com",
        "profile": "backend-dev", "track": "aws-backend-track",
    }, follow_redirects=False)
    assert web_response.status_code == 303

    api_state = load_bench_state("api@test.com")
    web_state = load_bench_state("web@test.com")
    assert api_state["profile_id"] == web_state["profile_id"]
    assert api_state["track_id"] == web_state["track_id"]
    assert len(api_state["tasks"]) == len(web_state["tasks"]) == 9


def test_report_and_checkin_contracts_return_committed_serializable_projections(client):
    response = client.post("/api/v1/onboard", json={
        "employee_name": "Cycle Person", "employee_email": "cycle@test.com",
        "profile_id": "backend-dev", "track_id": "aws-backend-track",
    })
    assert response.status_code == 200

    checkin = client.post("/api/v1/checkin", json={
        "employee_email": "CYCLE@Test.com", "period": "am",
        "planned": ["Review the first task"],
    })
    assert checkin.status_code == 200

    report = client.get("/api/v1/report/cycle@test.com")
    assert report.status_code == 200
    assert "reply" in report.json()
    with db_mod.connect() as conn:
        outbox = conn.execute(
            "SELECT status, person_id FROM report_outbox WHERE employee_email = ?",
            ("cycle@test.com",),
        ).fetchone()
    assert outbox["status"] == "completed"
    assert outbox["person_id"]


def test_teams_adapter_remains_free_of_bench_persistence_imports():
    tree = ast.parse(open("teams-bot/src/app.py", encoding="utf-8").read())
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    )
    assert "bench" not in imported
