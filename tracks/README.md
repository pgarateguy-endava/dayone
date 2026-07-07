# Bench tracks

A **track** is the declarative bench plan for a role: mandatory courses, certification
options, daily goals, profile-update tasks, portfolio projects, deadlines and responsibles.

Tracks never define permissions — access always comes from `profiles/*.yaml` (see ADR 0001).

## Schema

```yaml
id: string                      # file name without .yaml
name: string
target_profiles: [profile-id]   # which roles this track fits
duration_weeks: int
responsibles:                   # who receives the EOD report
  - name: string
    email: string
    role: people-lead | resourcing | capability-lead
deadlines:
  - id: string
    description: string
    due: YYYY-MM-DD
mandatory_courses:
  - id: string
    name: string
    provider: string
    est_hours: int
certification_options:
  - id: string
    name: string
    notes: string
profile_tasks: [string]         # Endava profile updates expected
portfolio_projects:
  - name: string
    description: string
    skills: [string]
daily_goals: [string]           # verified at each PM check-in
check_in_times: ["HH:MM", "HH:MM"]
practice_repos: [url]           # optional; consumed by the future repo-feedback bot (B4)
```
