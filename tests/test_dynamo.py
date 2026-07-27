from datetime import date, timedelta

import pytest

import bench.db as db_mod


@pytest.fixture()
def dynamo_env(tmp_path, monkeypatch):
    """Catalog + people stay in SQLite; notification/conversation state goes to DynamoDB
    (moto-mocked). Proves the BENCH_STORAGE=dynamodb path end-to-end without real AWS."""
    moto = pytest.importorskip("moto")
    monkeypatch.setattr(db_mod, "PROGRESS_DIR", tmp_path)
    monkeypatch.setenv("BENCH_STORAGE", "dynamodb")
    monkeypatch.setenv("BENCH_DYNAMODB_PREFIX", "bench-test")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    with moto.mock_aws():
        from bench.seed import seed

        seed()
        yield


def test_conversation_ref_and_notifications_roundtrip_on_dynamodb(dynamo_env):
    from bench import notify

    assert notify.has_conversation_ref("ada@test.com") is False
    notify.save_conversation_ref("ada@test.com", "conv-1")
    assert notify.has_conversation_ref("ada@test.com") is True

    # queue only lands when there's a conversation ref
    assert notify.queue_notification("ada@test.com", "kickoff", "hola") is True
    assert notify.queue_notification("nobody@test.com", "kickoff", "x") is False

    pending = notify.pending_notifications()
    assert len(pending) == 1 and pending[0]["conversation_id"] == "conv-1"
    notify.mark_delivered(pending[0]["id"])
    assert notify.pending_notifications() == []
    assert notify.notification_log("ada@test.com")[0]["kind"] == "kickoff"


def test_proactive_rules_run_against_dynamodb(dynamo_env):
    from bench import notify
    from bench.tools.state import set_bench_start_date, start_bench

    today = date.today()
    start_bench("Ada", "ada@test.com", "backend-dev", "aws-backend-track",
                bench_start_date=(today + timedelta(days=3)).isoformat())
    notify.save_conversation_ref("ada@test.com", "conv-ada")

    assert notify.generate_due_notifications() == 1
    assert notify.pending_notifications()[-1]["kind"] == "pre_bench_greeting"

    # changing the date clears DynamoDB notifications and re-fires (kickoff)
    set_bench_start_date("ada@test.com", (today - timedelta(days=1)).isoformat())
    assert notify.notification_log("ada@test.com") == []
    assert notify.generate_due_notifications() == 1
    assert notify.pending_notifications()[-1]["kind"] == "kickoff"
