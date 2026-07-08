"""Deterministic progress verification over task instances. (Read tool)

The LLM never decides progress: this function derives it from `person_tasks`
statuses, their freshness, and each task's follow-up frequency and deadline.
"""
from __future__ import annotations

from datetime import date as date_cls
from typing import Any

DEADLINE_WARNING_DAYS = 7

FOLLOW_UP_LABELS = {
    "twice_daily": "2x/day", "daily": "1x/day",
    "weekly": "1x/week", "biweekly": "every 2 weeks",
}


def _followed_up_today(follow_up: str, today: date_cls) -> bool:
    """Is this task due for AI follow-up today? (simplified calendar rules)"""
    if follow_up in ("twice_daily", "daily"):
        return True
    if follow_up == "weekly":
        return today.weekday() == 0  # Mondays
    if follow_up == "biweekly":
        return today.weekday() == 0 and today.isocalendar().week % 2 == 0
    return True


def verify_progress(state: dict, track: dict, on_date: str | None = None) -> dict[str, Any]:
    """Verify a person's bench progress for a given date.

    Returns overall completion, today's follow-up list (which tasks the AI must
    chase today and whether they were touched), blockers and deadline risks.
    """
    today = date_cls.fromisoformat(on_date) if on_date else date_cls.today()
    today_iso = today.isoformat()
    tasks = state.get("tasks", [])

    day_check_ins = [c for c in state.get("check_ins", []) if c["date"] == today_iso]
    blockers = [c["blockers"] for c in day_check_ins if c.get("blockers")]
    blocked_tasks = [t for t in tasks if t["status"] == "blocked"]
    blockers += [f"Task blocked: {t['title']}"
                 + (f" — {t['progress_note']}" if t["progress_note"] else "")
                 for t in blocked_tasks]

    done = [t for t in tasks if t["status"] == "done"]
    follow_up_today = []
    for task in tasks:
        if task["status"] == "done" or not _followed_up_today(task["follow_up"], today):
            continue
        touched = bool(task["updated_at"] and task["updated_at"][:10] == today_iso)
        missing_evidence = bool(task["evidence_required"]) and touched and not task["evidence"]
        follow_up_today.append({
            "task_id": task["task_id"], "title": task["title"], "category": task["category"],
            "status": task["status"], "follow_up": task["follow_up"],
            "touched_today": touched, "evidence": task["evidence"],
            "missing_evidence": missing_evidence,
        })

    deadlines = []
    for task in tasks:
        if not task["due_date"]:
            continue
        days_left = (date_cls.fromisoformat(task["due_date"]) - today).days
        if task["status"] == "done":
            level = "done"
        elif days_left < 0:
            level = "overdue"
        elif days_left <= DEADLINE_WARNING_DAYS:
            level = "at_risk"
        else:
            level = "ok"
        deadlines.append({"task_id": task["task_id"], "title": task["title"],
                          "due": task["due_date"], "days_left": days_left, "level": level})

    total = len(tasks)
    touched_count = sum(1 for f in follow_up_today if f["touched_today"])
    return {
        "date": today_iso,
        "checked_in_am": any(c["period"] == "am" for c in day_check_ins),
        "checked_in_pm": any(c["period"] == "pm" for c in day_check_ins),
        "tasks_total": total,
        "tasks_done": len(done),
        "completion_rate": round(len(done) / total, 2) if total else 0.0,
        "follow_up_today": follow_up_today,
        "touched_today": touched_count,
        "pending_today": len(follow_up_today) - touched_count,
        "blockers": blockers,
        "deadlines": deadlines,
    }
