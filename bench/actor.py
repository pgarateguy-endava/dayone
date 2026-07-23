"""Explicit local actor context shared by every Bench channel and tool."""
from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

DEFAULT_ACTOR = "local-operator"

_actor_override: ContextVar[str | None] = ContextVar("bench_actor_override", default=None)


def resolve_actor() -> str:
    """Resolve the configured actor at call time with a safe local fallback."""
    configured = os.environ.get("BENCH_ACTOR")
    return configured if configured and configured.strip() else DEFAULT_ACTOR


def current_actor() -> str:
    """Return the scoped actor override or the current environment-derived actor."""
    override = _actor_override.get()
    return override if override is not None else resolve_actor()


@contextmanager
def actor_context(value: str | None = None) -> Iterator[str]:
    """Temporarily override the actor and always restore the previous context.

    ``None`` establishes no override, allowing the environment/fallback resolver to
    remain authoritative. Explicit blank values are rejected so mutations cannot run
    under an anonymous actor.
    """
    if value is None:
        yield current_actor()
        return
    if not value.strip():
        raise ValueError("actor must not be blank")
    token = _actor_override.set(value)
    try:
        yield value
    finally:
        _actor_override.reset(token)
