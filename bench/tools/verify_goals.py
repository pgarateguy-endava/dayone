"""Deterministic goal and deadline verification. (Read tool)

The LLM never decides completion: this function does, from recorded check-ins.
"""
from __future__ import annotations

from datetime import date as date_cls
from typing import Any

DEADLINE_WARNING_DAYS = 7


def verify_daily_goals(state: dict, track: dict, on_date: str | None = None) -> dict[str, Any]:
    """Compare the track's daily goals against the day's PM check-ins.

    Returns goals met/missed, completion rate, blockers and deadline risk flags.
    """
    today = on_date or date_cls.today().isoformat()
    daily_goals = track.get("daily_goals", [])

    day_check_ins = [c for c in state.get("check_ins", []) if c["date"] == today]
    pm_check_ins = [c for c in day_check_ins if c["period"] == "pm"]

    done_indexes: set[int] = set()
    evidence: dict[int, list[str]] = {}
    blockers: list[str] = []
    for check_in in day_check_ins:
        if check_in.get("blockers"):
            blockers.append(check_in["blockers"])
    for check_in in pm_check_ins:
        for item in check_in.get("done_goals", []):
            idx = int(item["goal"])
            if 1 <= idx <= len(daily_goals):
                done_indexes.add(idx)
                if item.get("evidence"):
                    evidence.setdefault(idx, []).append(item["evidence"])

    met = [{"goal": i, "text": daily_goals[i - 1], "evidence": evidence.get(i, [])}
           for i in sorted(done_indexes)]
    missed = [{"goal": i, "text": g} for i, g in enumerate(daily_goals, start=1)
              if i not in done_indexes]

    deadline_risks = []
    for deadline in track.get("deadlines", []):
        days_left = (date_cls.fromisoformat(str(deadline["due"])) - date_cls.fromisoformat(today)).days
        if days_left < 0:
            level = "overdue"
        elif days_left <= DEADLINE_WARNING_DAYS:
            level = "at_risk"
        else:
            level = "ok"
        deadline_risks.append({**deadline, "due": str(deadline["due"]),
                               "days_left": days_left, "level": level})

    total = len(daily_goals)
    return {
        "date": today,
        "checked_in_am": any(c["period"] == "am" for c in day_check_ins),
        "checked_in_pm": bool(pm_check_ins),
        "goals_total": total,
        "goals_met": len(met),
        "completion_rate": round(len(met) / total, 2) if total else 0.0,
        "met": met,
        "missed": missed,
        "blockers": blockers,
        "deadlines": deadline_risks,
    }
