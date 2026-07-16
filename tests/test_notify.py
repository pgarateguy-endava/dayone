from datetime import date, timedelta

import pytest

import bench.db as db_mod
from bench.notify import (
    generate_due_notifications,
    mark_delivered,
    pending_notifications,
    save_conversation_ref,
)
from bench.seed import seed
from bench.tools.knowledge import suggest_for_profile
from bench.tools.state import load_bench_state, mark_profile_update_done, start_bench


@pytest.fixture()
def seeded(tmp_path, monkeypatch):
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    seed()
    return tmp_path


def test_suggestions_match_profile_tags(seeded):
    result = suggest_for_profile("Senior developer with strong AWS and Python background")
    assert any("Claude Partner Network" in m["title"] for m in result["mandatory"])
    assert any("Solutions Architect" in c["title"] for c in result["certifications"])
    assert all("Azure" not in c["title"] for c in result["certifications"])  # no azure in profile


def test_proactive_rules_pre_bench_kickoff_and_progress(seeded):
    today = date.today()
    # future date -> computed pre_bench -> greeting
    start_bench("Ana", "ana@test.com", "backend-dev", "aws-backend-track",
                bench_start_date=(today + timedelta(days=5)).isoformat())
    # date 10 days ago -> computed active -> kickoff first, then weekly progress check
    start_bench("Beto", "beto@test.com", "backend-dev", "aws-backend-track",
                bench_start_date=(today - timedelta(days=10)).isoformat(),
                profile_text="worked with aws lambda")
    assert generate_due_notifications() == 2
    save_conversation_ref("ana@test.com", "conv-ana")
    pending = pending_notifications()
    kinds = {p["email"]: p["kind"] for p in pending}
    assert kinds["ana@test.com"] == "pre_bench_greeting"
    assert kinds["beto@test.com"] == "kickoff"
    assert "actualizar tu Endava Profile" in [p for p in pending if p["email"] == "ana@test.com"][0]["message"]
    assert "planificar un bench exitoso" in [p for p in pending if p["email"] == "ana@test.com"][0]["message"]
    assert "Claude Partner Network" in [p for p in pending if p["email"] == "beto@test.com"][0]["message"]
    ana = [p for p in pending if p["email"] == "ana@test.com"][0]
    assert ana["conversation_id"] == "conv-ana"

    # idempotent: nothing new queued immediately after
    assert generate_due_notifications() == 0
    # deliver kickoff -> next run queues Beto's weekly progress check
    beto_id = [p for p in pending if p["email"] == "beto@test.com"][0]["id"]
    mark_delivered(beto_id)
    assert generate_due_notifications() == 1
    assert pending_notifications()[-1]["kind"] == "progress_check"


def test_changing_the_date_recomputes_status_and_refires(seeded):
    from bench.tools.state import computed_status, set_bench_start_date

    today = date.today()
    start_bench("Caro", "caro@test.com", "backend-dev", "aws-backend-track")
    assert load_bench_state("caro@test.com")["status"] == "inactive"  # no date
    assert generate_due_notifications() == 0  # inactive -> bot silent

    # demo step 1: date in a few days -> pre_bench -> greeting fires
    set_bench_start_date("caro@test.com", (today + timedelta(days=3)).isoformat())
    assert load_bench_state("caro@test.com")["status"] == "pre_bench"
    assert generate_due_notifications() == 1
    assert pending_notifications()[-1]["kind"] == "pre_bench_greeting"

    # demo step 2: date a week ago -> active -> history cleared, kickoff fires
    set_bench_start_date("caro@test.com", (today - timedelta(days=7)).isoformat())
    assert load_bench_state("caro@test.com")["status"] == "active"
    assert generate_due_notifications() == 1
    assert pending_notifications()[-1]["kind"] == "kickoff"
    assert computed_status(None) == "inactive"


def test_planning_prompt_fires_one_day_before_bench(seeded):
    today = date.today()
    start_bench("Dani", "dani@test.com", "backend-dev", "aws-backend-track",
                bench_start_date=(today + timedelta(days=1)).isoformat())

    assert generate_due_notifications() == 1
    pending = pending_notifications()
    assert pending[0]["kind"] == "planning_prompt"
    assert "Mañana entrás en bench" in pending[0]["message"]
    assert "planificar tu período en bench" in pending[0]["message"]
    assert generate_due_notifications() == 0


def test_mark_profile_update_done_finds_employee_task(seeded):
    start_bench("Elena", "elena@test.com", "backend-dev", "aws-backend-track")

    result = mark_profile_update_done("elena@test.com", "Hoy terminé de preparar el profile")

    assert result["title"] == "Update Endava profile"
    state = load_bench_state("elena@test.com")
    profile_task = [t for t in state["tasks"] if t["category"] == "profile_update"][0]
    assert profile_task["status"] == "done"
    assert "preparar el profile" in profile_task["evidence"]


def test_conversation_ref_email_case_does_not_block_delivery(seeded):
    today = date.today()
    start_bench("Pedro", "pedro.garateguy@endava.com", "backend-dev", "aws-backend-track",
                bench_start_date=(today + timedelta(days=5)).isoformat())

    assert generate_due_notifications() == 1
    save_conversation_ref("Pedro.Garateguy@Endava.com", "conv-pedro")

    pending = pending_notifications()
    assert len(pending) == 1
    assert pending[0]["email"] == "pedro.garateguy@endava.com"
    assert pending[0]["conversation_id"] == "conv-pedro"
