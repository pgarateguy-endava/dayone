"""End-of-day report for the responsibles. (Generation + Write tool)

MVP: writes Markdown to .local-progress/reports/. Production: Teams webhook/Graph API.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bench.config import REPORTS_DIR
from bench.tools.verify_goals import FOLLOW_UP_LABELS

_LEVEL_LABEL = {"overdue": "OVERDUE", "at_risk": "AT RISK", "ok": "ok", "done": "done"}


def build_eod_report(
    state: dict[str, Any],
    track: dict[str, Any],
    verification: dict[str, Any],
    summary: str = "",
) -> str:
    """Render the EOD report Markdown from a verification result."""
    followed = []
    for item in verification["follow_up_today"]:
        mark = "x" if item["touched_today"] else " "
        extra = f" — evidence: {item['evidence']}" if item["evidence"] else ""
        if item["missing_evidence"]:
            extra = " — ⚠ evidence required but missing"
        followed.append(
            f"[{mark}] {item['title']} ({item['status']}, "
            f"{FOLLOW_UP_LABELS.get(item['follow_up'], item['follow_up'])}){extra}")

    deadlines = [f"`{d['due']}` ({d['days_left']:+d}d, {_LEVEL_LABEL[d['level']]}) — {d['title']}"
                 for d in verification["deadlines"] if d["level"] != "done"]
    responsibles = ", ".join(r["email"] for r in track.get("responsibles", [])) or "pending"

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- None."

    return f"""# EOD report - {state['employee_name']} - {verification['date']}

**To:** {responsibles}
**Track:** {track.get('name')} | **Profile:** {state['profile_id']}
**Check-ins today:** AM {'yes' if verification['checked_in_am'] else 'NO'} / PM {'yes' if verification['checked_in_pm'] else 'NO'}
**Overall:** {verification['tasks_done']}/{verification['tasks_total']} tasks done ({int(verification['completion_rate'] * 100)}%)
**Today's follow-up:** {verification['touched_today']} touched / {verification['pending_today']} untouched

## Summary

{summary or 'Deterministic report (LLM summary disabled).'}

## Tasks followed up today

{bullets(followed)}

## Blockers

{bullets(verification['blockers'])}

## Deadlines

{bullets(deadlines)}

---
*Simulated delivery: in production this report is sent to Teams and persisted in DynamoDB.*
"""


def save_eod_report(report_md: str, employee_email: str, on_date: str) -> str:
    """Write the report to .local-progress/reports/ and return its path. (Write tool)"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(REPORTS_DIR) / f"{on_date}_{employee_email.replace('@', '_at_')}.md"
    path.write_text(report_md, encoding="utf-8")
    return str(path)
