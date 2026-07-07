"""Local bench state. (Write/Read tools)

File-based on purpose for the MVP; in production these functions become DynamoDB
reads/writes keyed by employee email (same pattern as agent/tools/track_progress.py).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import json
from typing import Any

from bench.config import PROGRESS_DIR


def _state_path(employee_email: str) -> Path:
    return Path(PROGRESS_DIR) / f"bench_{employee_email.replace('@', '_at_')}.json"


def start_bench(employee_name: str, employee_email: str, profile_id: str, track_id: str) -> dict:
    """Create (or reset) the bench state record for a person. (Write tool)"""
    PROGRESS_DIR.mkdir(exist_ok=True)
    state = {
        "employee_name": employee_name,
        "employee_email": employee_email,
        "profile_id": profile_id,
        "track_id": track_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "check_ins": [],
    }
    _state_path(employee_email).write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return state


def load_bench_state(employee_email: str) -> dict[str, Any]:
    """Load the bench state for a person. (Read tool)"""
    path = _state_path(employee_email)
    if not path.exists():
        raise FileNotFoundError(
            f"No bench state for '{employee_email}'. Run: python -m bench.app start ..."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def record_check_in(
    employee_email: str,
    period: str,
    done_goals: list[dict] | None = None,
    planned: list[str] | None = None,
    blockers: str = "",
    note: str = "",
) -> dict:
    """Record an AM or PM check-in. (Write tool)

    - period: "am" (declare today's focus) or "pm" (declare completions with evidence).
    - done_goals: list of {"goal": <1-based index into track daily_goals>, "evidence": str}.
    """
    if period not in ("am", "pm"):
        raise ValueError("period must be 'am' or 'pm'")
    state = load_bench_state(employee_email)
    event = {
        "date": date.today().isoformat(),
        "period": period,
        "done_goals": done_goals or [],
        "planned": planned or [],
        "blockers": blockers,
        "note": note,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    state["check_ins"].append(event)
    _state_path(employee_email).write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return event
