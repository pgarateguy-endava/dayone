import asyncio

import pytest

from bench.actor import actor_context, current_actor, resolve_actor


def test_resolve_actor_uses_configured_value_at_call_time(monkeypatch):
    monkeypatch.setenv("BENCH_ACTOR", "operator@example.com")

    assert resolve_actor() == "operator@example.com"

    monkeypatch.setenv("BENCH_ACTOR", "second-operator")
    assert resolve_actor() == "second-operator"


@pytest.mark.parametrize("value", [None, "", "   ", "\t\n"])
def test_resolve_actor_falls_back_for_unset_or_blank_values(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("BENCH_ACTOR", raising=False)
    else:
        monkeypatch.setenv("BENCH_ACTOR", value)

    assert resolve_actor() == "local-operator"
    assert current_actor() == "local-operator"


def test_actor_context_override_is_scoped_and_restored(monkeypatch):
    monkeypatch.setenv("BENCH_ACTOR", "environment-operator")

    assert current_actor() == "environment-operator"
    with actor_context("test-operator"):
        assert current_actor() == "test-operator"
        with actor_context("nested-operator"):
            assert current_actor() == "nested-operator"
        assert current_actor() == "test-operator"
    assert current_actor() == "environment-operator"


def test_actor_context_restores_after_exception(monkeypatch):
    monkeypatch.setenv("BENCH_ACTOR", "environment-operator")

    with pytest.raises(RuntimeError):
        with actor_context("failing-test"):
            assert current_actor() == "failing-test"
            raise RuntimeError("mutation failed")

    assert current_actor() == "environment-operator"


def test_blank_explicit_override_is_rejected(monkeypatch):
    monkeypatch.setenv("BENCH_ACTOR", "environment-operator")

    with pytest.raises(ValueError, match="actor"):
        with actor_context("  "):
            pass

    assert current_actor() == "environment-operator"


def test_actor_context_isolated_between_async_tasks(monkeypatch):
    monkeypatch.setenv("BENCH_ACTOR", "environment-operator")

    async def read_actor(value):
        with actor_context(value):
            await asyncio.sleep(0)
            return current_actor()

    async def run():
        return await asyncio.gather(read_actor("first"), read_actor("second"))

    assert asyncio.run(run()) == ["first", "second"]
    assert current_actor() == "environment-operator"
