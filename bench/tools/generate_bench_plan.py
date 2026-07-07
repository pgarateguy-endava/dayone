"""Deterministic bench plan generator. (Generation tool — no LLM, same stance as onboarding J1)."""
from typing import Any


def _bullet(items: list[Any], indent: int = 0) -> str:
    prefix = " " * indent + "- "
    return "\n".join(prefix + str(item) for item in items) if items else prefix + "Pending."


def generate_bench_plan(
    employee_name: str,
    employee_email: str,
    profile: dict[str, Any],
    track: dict[str, Any],
) -> str:
    """Generate a personalized bench plan as Markdown from profile + track YAML."""
    courses = [
        f"**{c['name']}** ({c.get('provider', 'provider pending')}, ~{c.get('est_hours', '?')}h)"
        for c in track.get("mandatory_courses", [])
    ]
    certs = [
        f"**{c['name']}** — {c.get('notes', '')}" for c in track.get("certification_options", [])
    ]
    deadlines = [
        f"`{d['due']}` — {d['description']}" for d in track.get("deadlines", [])
    ]
    responsibles = [
        f"{r['name']} <{r['email']}> ({r.get('role', 'responsible')})"
        for r in track.get("responsibles", [])
    ]
    projects = [
        f"**{p['name']}**: {p.get('description', '')} _(skills: {', '.join(p.get('skills', []))})_"
        for p in track.get("portfolio_projects", [])
    ]
    goals = [f"{i}. {g}" for i, g in enumerate(track.get("daily_goals", []), start=1)]
    approvals = profile.get("approvals_required", [])

    return f"""# Bench plan - {employee_name}

**Employee:** {employee_name}
**Email:** {employee_email}
**Profile:** {profile.get('name', profile.get('id'))}
**Track:** {track.get('name', track.get('id'))} ({track.get('duration_weeks', '?')} weeks)

## Responsibles (receive the EOD report)

{_bullet(responsibles)}

## Deadlines

{_bullet(deadlines)}

## Mandatory courses

{_bullet(courses)}

## Certification options

{_bullet(certs)}

## Profile update tasks

{_bullet(track.get('profile_tasks', []))}

Reference documentation: {', '.join(track.get('profile_docs', [])) or 'pending'}

## Portfolio project suggestions

{_bullet(projects)}

## Daily goals (verified at each PM check-in)

{chr(10).join(goals) if goals else '- Pending.'}

Check-in times: {', '.join(track.get('check_in_times', [])) or 'pending'}

## Access during bench

Access remains role-based from your profile (`profiles/{profile.get('id')}.yaml`).
This plan never grants permissions. Actions requiring human approval:

{_bullet(approvals)}

---
*MVP status: data comes from local versioned YAML; progress is stored locally and the
EOD report is written to disk. In production: DynamoDB state, Teams delivery,
Bedrock Knowledge Base for profile documentation.*
"""
