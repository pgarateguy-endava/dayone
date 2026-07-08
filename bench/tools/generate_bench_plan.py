"""Deterministic bench plan generator from the relational catalog. (Generation tool — no LLM)"""
from typing import Any

from bench.tools.verify_goals import FOLLOW_UP_LABELS

_CATEGORY_TITLES = {
    "course": "Courses", "certification": "Certifications",
    "profile_update": "Profile updates", "portfolio": "Portfolio projects", "admin": "Admin",
}


def _task_lines(task: dict[str, Any]) -> str:
    meta = [FOLLOW_UP_LABELS.get(task["follow_up"], task["follow_up"]) + " follow-up"]
    if task.get("due_date"):
        meta.append(f"due `{task['due_date']}`")
    if task.get("est_hours"):
        meta.append(f"~{task['est_hours']:g}h")
    if task.get("requires_approval"):
        meta.append("requires approval")
    lines = [f"- **{task['title']}** ({', '.join(meta)})"]
    if task.get("description"):
        lines.append(f"  - {task['description']}")
    if task.get("link"):
        lines.append(f"  - Link: {task['link']}")
    for contact in task.get("contacts", []):
        who = f"{contact['name']}" + (f" <{contact['email']}>" if contact["email"] else "")
        note = f" — {contact['note']}" if contact["note"] else ""
        lines.append(f"  - Contact: {who}{note}")
    return "\n".join(lines)


def generate_bench_plan(
    employee_name: str,
    employee_email: str,
    profile: dict[str, Any],
    track: dict[str, Any],
) -> str:
    """Generate a personalized bench plan as Markdown from the DB catalog."""
    sections = []
    for category, title in _CATEGORY_TITLES.items():
        tasks = [t for t in track.get("tasks", []) if t["category"] == category]
        if tasks:
            sections.append(f"## {title}\n\n" + "\n".join(_task_lines(t) for t in tasks))

    responsibles = "\n".join(
        f"- {r['name']} <{r['email']}> ({r['role']})" for r in track.get("responsibles", [])
    ) or "- Pending."
    aws = ", ".join(profile.get("permissions", {}).get("aws", [])) or "none"
    approvals = "\n".join(f"- {a}" for a in profile.get("approvals_required", [])) or "- None."

    return f"""# Bench plan - {employee_name}

**Employee:** {employee_name}
**Email:** {employee_email}
**Profile:** {profile.get('name', profile.get('id'))}
**Track:** {track.get('name', track.get('id'))} ({track.get('duration_weeks', '?')} weeks)

## Responsibles (receive the EOD report)

{responsibles}

{chr(10).join(sections)}

## Follow-up

The assistant checks in twice a day (AM plan / PM completions) and verifies each task
according to its follow-up frequency. Evidence is expected for tasks that require it
(course %, commit URL, profile diff).

## Access during bench

Access remains role-based from your profile (AWS: {aws}).
This plan never grants permissions. Actions requiring human approval:

{approvals}

---
*Dev status: catalog and state live in SQLite (`.local-progress/bench.db`); reports are
written to disk. In production: DynamoDB, Teams delivery, Bedrock Knowledge Base.*
"""
