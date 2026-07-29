"""Stable domain operation contracts shared by Bench channels.

Channels translate native input and presentation around these helpers.  The
helpers deliberately contain no HTTP, HTML, CLI, or Teams concerns and return
serializable committed values rather than database rows or connections.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Callable, TypeVar

from bench.db import normalize_email

T = TypeVar("T")

_LOOKUP_OPERATIONS = {"load_person", "load_profile", "load_track", "load_task",
                      "get_knowledge", "load_person_history"}
_VALIDATION_OPERATIONS = {"onboard_person", "update_task_status", "record_check_in",
                          "save_conversation_ref", "mark_notification_delivered",
                          "create_track", "update_task", "add_knowledge", "update_knowledge",
                          "add_responsible", "set_bench_start_date"}
_PROTECTED_OPERATIONS = {"delete_profile", "delete_track", "delete_task"}


@dataclass(frozen=True)
class DomainResult:
    """The committed result of one named domain operation."""

    operation: str
    data: T

    def __post_init__(self) -> None:
        try:
            json.dumps(self.data)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{self.operation} returned a non-serializable domain projection"
            ) from exc

    def as_dict(self) -> dict[str, Any]:
        return {"operation": self.operation, "data": self.data}


class DomainError(Exception):
    """Expected, channel-neutral failure with stable classification."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None,
                 safe_message: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.safe_message = safe_message or message
        self.details = details or {}


def _classify_error(exc: Exception) -> DomainError:
    message = str(exc).strip("'")
    if isinstance(exc, FileNotFoundError):
        return DomainError("not_found", message, safe_message="Requested resource was not found.")
    if isinstance(exc, KeyError):
        return DomainError("not_found", message, safe_message="Requested resource was not found.")
    if isinstance(exc, ValueError):
        return DomainError("validation", message, safe_message="The request could not be validated.")
    return DomainError("internal", message)


def execute(operation: str, fn: Callable[..., T], *args: Any, **kwargs: Any) -> DomainResult:
    """Execute a shared tool and normalize expected failures.

    Unexpected exceptions retain their original type and traceback.  This
    helper only translates the domain errors currently exposed by the legacy
    tools, so adapters no longer branch on exception strings.
    """
    try:
        return DomainResult(operation, fn(*args, **kwargs))
    except DomainError:
        raise
    except FileNotFoundError as exc:
        raise _classify_error(exc) from exc
    except KeyError as exc:
        if operation not in _LOOKUP_OPERATIONS and operation not in _VALIDATION_OPERATIONS:
            raise
        raise _classify_error(exc) from exc
    except ValueError as exc:
        if operation not in _VALIDATION_OPERATIONS and operation not in _PROTECTED_OPERATIONS:
            raise
        code = "protected" if operation in _PROTECTED_OPERATIONS else "validation"
        raise DomainError(code, str(exc), safe_message=str(exc)) from exc


def require_email(value: str) -> str:
    """Normalize a channel email once and reject unusable input."""
    if not isinstance(value, str) or not value.strip():
        raise DomainError("validation", "email is required", details={"field": "email"})
    normalized = normalize_email(value)
    email_pattern = r"^[^@\s/\\\x00-\x1f\x7f]+@[^@\s/\\\x00-\x1f\x7f]+\.[^@\s/\\\x00-\x1f\x7f]+$"
    if len(normalized) > 320 or not re.fullmatch(email_pattern, normalized):
        raise DomainError("validation", "email must be a valid address",
                          details={"field": "email"},
                          safe_message="Email must be a valid address.")
    return normalized


def onboard_person(employee_name: str, employee_email: str, profile_id: str, track_id: str,
                    *, bench_start_date: str | None = None, profile_text: str = "",
                    profile_filename: str = "", starter: Callable[..., dict] | None = None
                    ) -> DomainResult:
    """Create the person and reconcile immediate notifications from committed state."""
    from bench.tools.state import start_bench

    start = starter or start_bench
    normalized_email = require_email(employee_email)
    if bench_start_date is None and not profile_text and not profile_filename:
        state = execute("onboard_person", start, employee_name, normalized_email,
                        profile_id, track_id).data
    else:
        state = execute("onboard_person", start, employee_name, normalized_email,
                        profile_id, track_id, bench_start_date=bench_start_date,
                        profile_text=profile_text, profile_filename=profile_filename).data
    try:
        from bench.notify import generate_due_notifications

        generate_due_notifications()
    except Exception:  # scheduler reconciliation retries from committed state
        state = {**state, "notification_reconciliation_pending": True}
    return DomainResult("onboard_person", state)


def load_person(employee_email: str) -> DomainResult:
    from bench.tools.state import load_bench_state

    return execute("load_person", load_bench_state, require_email(employee_email))


def update_person_task(employee_email: str, task_id: int, status: str,
                       evidence: str = "", note: str = "",
                       updater: Callable[..., dict] | None = None) -> DomainResult:
    from bench.tools.state import update_task_status

    return execute("update_task_status", updater or update_task_status,
                   require_email(employee_email), task_id, status, evidence, note)


def set_person_bench_start(employee_email: str, bench_start_date: str | None) -> DomainResult:
    from bench.tools.state import set_bench_start_date

    return execute("set_bench_start_date", set_bench_start_date,
                   require_email(employee_email), bench_start_date)


def run_checkin_cycle(employee_email: str, period: str, *, planned: list[str] | None = None,
                      blockers: str = "", task_updates: list[dict] | None = None) -> DomainResult:
    from bench.graph import build_graph

    if period not in ("am", "pm"):
        raise DomainError("validation", "period must be 'am' or 'pm'",
                          safe_message="Period must be 'am' or 'pm'.")
    result = build_graph().invoke({
        "employee_email": require_email(employee_email), "period": period,
        "planned": planned or [], "blockers": blockers,
        "task_updates": task_updates or [],
    })
    return DomainResult("record_check_in", result)


def save_person_report(employee_email: str, on_date: str | None = None) -> DomainResult:
    from bench.tools.catalog import load_track
    from bench.tools.eod_report import build_eod_report, save_eod_report
    from bench.tools.verify_goals import verify_progress

    state = load_person(employee_email).data
    track = execute("load_track", load_track, state["track_id"]).data
    verification = verify_progress(state, track, on_date)
    report = build_eod_report(state, track, verification)
    path = save_eod_report(report, state["employee_email"], verification["date"])
    return DomainResult("save_person_report", {
        "report": report, "path": path, "date": verification["date"],
        "person_id": state["person_id"],
    })


def generate_notifications() -> DomainResult:
    """Evaluate notification rules and return the committed queue count."""
    from bench.notify import generate_due_notifications

    return execute("generate_due_notifications", generate_due_notifications)


def mark_profile_done(employee_email: str, evidence: str = "") -> DomainResult:
    from bench.tools.state import mark_profile_update_done

    return execute("mark_profile_update_done", mark_profile_update_done,
                   require_email(employee_email), evidence=evidence)


def mark_named_task_done(employee_email: str, text: str, evidence: str = "") -> DomainResult:
    from bench.tools.state import mark_task_done_by_title

    return execute("mark_task_done_by_title", mark_task_done_by_title,
                   require_email(employee_email), text, evidence=evidence)


def update_catalog_task(task_id: int, **fields: Any) -> DomainResult:
    from bench.tools.catalog import update_task

    return execute("update_task", update_task, task_id, **fields)


def delete_catalog_task(task_id: int) -> DomainResult:
    from bench.tools.catalog import delete_task

    return execute("delete_task", delete_task, task_id)


def update_knowledge_item(item_id: int, **fields: Any) -> DomainResult:
    from bench.tools.knowledge import update_knowledge

    return execute("update_knowledge", update_knowledge, item_id, **fields)


def delete_knowledge_item(item_id: int) -> DomainResult:
    from bench.tools.knowledge import delete_knowledge

    return execute("delete_knowledge", delete_knowledge, item_id)
