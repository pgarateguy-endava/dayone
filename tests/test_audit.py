import json
import sqlite3

import pytest

import bench.db as db_mod
from bench.actor import actor_context
from bench.db import update_person_email
from bench.seed import seed
from bench.tools.audit import append_audit, list_action_history
from bench.tools.state import start_bench, update_task_status


def test_audit_append_and_person_history_are_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    seed()
    with actor_context("audit-operator"):
        state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
        update_task_status("ada@test.com", state["tasks"][0]["task_id"], "done")

    history = list_action_history(person_id=state["person_id"])
    assert [row["action"] for row in history[:2]] == ["update_task_status", "start_bench"]
    assert all(row["actor"] == "audit-operator" for row in history)
    assert history[0]["person_id"] == state["person_id"]
    assert isinstance(history[0]["context"], dict)


def test_audit_row_rolls_back_with_mutation_transaction(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    with actor_context("rollback-operator"), pytest.raises(RuntimeError):
        with db_mod.connect() as conn:
            append_audit(conn, entity_type="task", entity_id=1, action="test_mutation")
            raise RuntimeError("mutation failed")

    with db_mod.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0


def test_audit_log_is_append_only(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    with actor_context("append-only-operator"), db_mod.connect() as conn:
        row_id = append_audit(conn, entity_type="task", entity_id=1, action="created")
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute("UPDATE audit_log SET outcome = 'changed' WHERE id = ?", (row_id,))
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute("DELETE FROM audit_log WHERE id = ?", (row_id,))


def test_audit_context_is_stable_json(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    with actor_context("context-operator"), db_mod.connect() as conn:
        append_audit(conn, entity_type="person", entity_id="p1", action="updated",
                     context={"z": 1, "a": "value"})
        stored = conn.execute("SELECT context FROM audit_log").fetchone()[0]
    assert stored == json.dumps({"a": "value", "z": 1}, separators=(",", ":"))


def test_email_change_keeps_person_history_attached(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    seed()
    with actor_context("identity-operator"):
        state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
        update_person_email("ada@test.com", "ada.new@test.com")

    history = list_action_history(person_id=state["person_id"])
    assert history[0]["action"] == "update_person_email"
    assert history[0]["person_id"] == state["person_id"]
    assert history[0]["context"] == {
        "new_email": "ada.new@test.com",
        "old_email": "ada@test.com",
    }


def test_rejected_task_mutation_does_not_append_success_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    seed()
    with actor_context("rejection-operator"):
        state = start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
        with pytest.raises(KeyError, match="not assigned"):
            update_task_status("ada@test.com", 999999, "done")

    history = list_action_history(person_id=state["person_id"])
    assert [row["action"] for row in history] == ["start_bench"]


def test_materialized_task_and_completion_roll_back_together(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    seed()
    with actor_context("rollback-operator"):
        start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
        with db_mod.connect() as conn:
            task_id = conn.execute(
                "SELECT id FROM tasks WHERE title = 'Claude Partner Network Learning Path'"
            ).fetchone()[0]
            conn.execute("DELETE FROM person_tasks WHERE task_id = ?", (task_id,))
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        def fail_audit(*args, **kwargs):
            raise RuntimeError("audit unavailable")

        monkeypatch.setattr("bench.tools.state.append_audit", fail_audit)
        with pytest.raises(RuntimeError, match="audit unavailable"):
            from bench.tools.state import mark_task_done_by_title

            mark_task_done_by_title("ada@test.com", "Claude Partner Network Learning Path")
        monkeypatch.setattr("bench.tools.state.append_audit", append_audit)

    with db_mod.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE track_id = 'aws-backend-track' "
            "AND title = 'Claude Partner Network Learning Path'"
        ).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1


def test_report_outbox_reconciles_after_audit_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    seed()
    start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track")
    report_file = tmp_path / "reports" / "2026-07-27_ada_at_test.com.md"
    monkeypatch.setattr("bench.docstore.put_report", lambda filename, content: str(report_file))

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("bench.tools.eod_report.append_audit", fail_audit)
    from bench.tools.eod_report import reconcile_report_outbox, save_eod_report

    with pytest.raises(RuntimeError, match="audit unavailable"):
        save_eod_report("report", "ada@test.com", "2026-07-27")
    with db_mod.connect() as conn:
        assert conn.execute(
            "SELECT status FROM report_outbox WHERE filename = '2026-07-27_ada_at_test.com.md'"
        ).fetchone()[0] == "pending"

    monkeypatch.setattr("bench.tools.eod_report.append_audit", append_audit)
    assert reconcile_report_outbox() == 1
    with db_mod.connect() as conn:
        assert conn.execute(
            "SELECT status FROM report_outbox WHERE filename = '2026-07-27_ada_at_test.com.md'"
        ).fetchone()[0] == "completed"
        assert conn.execute(
            "SELECT action FROM audit_log WHERE entity_type = 'report'"
        ).fetchone()[0] == "save_eod_report"
