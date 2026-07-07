"""End-of-day report for the responsibles. (Generation + Write tool)

MVP: writes Markdown to .local-progress/reports/. Production: Teams webhook/Graph API.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bench.config import REPORTS_DIR

_LEVEL_LABEL = {"overdue": "OVERDUE", "at_risk": "AT RISK", "ok": "ok"}


def build_eod_report(
    state: dict[str, Any],
    track: dict[str, Any],
    verification: dict[str, Any],
    summary: str = "",
) -> str:
    """Render the EOD report Markdown from a verification result."""
    met = [f"[x] ({m['goal']}) {m['text']}"
           + (f" — evidence: {', '.join(m['evidence'])}" if m["evidence"] else " — no evidence")
           for m in verification["met"]]
    missed = [f"[ ] ({m['goal']}) {m['text']}" for m in verification["missed"]]
    deadlines = [f"`{d['due']}` ({d['days_left']:+d}d, {_LEVEL_LABEL[d['level']]}) — {d['description']}"
                 for d in verification["deadlines"]]
    blockers = verification["blockers"]
    responsibles = ", ".join(r["email"] for r in track.get("responsibles", [])) or "pending"

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- None."

    return f"""# EOD report - {state['employee_name']} - {verification['date']}

**To:** {responsibles}
**Track:** {track.get('name')} | **Profile:** {state['profile_id']}
**Check-ins today:** AM {'yes' if verification['checked_in_am'] else 'NO'} / PM {'yes' if verification['checked_in_pm'] else 'NO'}
**Daily goals:** {verification['goals_met']}/{verification['goals_total']} ({int(verification['completion_rate'] * 100)}%)

## Summary

{summary or 'Deterministic report (LLM summary disabled).'}

## Goals met

{bullets(met)}

## Goals missed

{bullets(missed)}

## Blockers

{bullets(blockers)}

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
