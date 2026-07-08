# ADR 0003: Relational catalog in SQLite (no more YAML for the Bench domain)

- **Status:** accepted
- **Date:** 2026-07-08

## Context

The first Bench iteration stored tracks as YAML edited via a textarea. That hid the real
model: a track has **one-to-many tasks**, and each task has its own deadline, follow-up
frequency, reference contacts and estimated effort. Task **status belongs to the person's
instance** (`person_tasks`), not to the catalog task (template) — the same course can be
`done` for Ada and `blocked` for Pedro.

## Decision

Move the whole Bench catalog to SQLite (`bench/db.py`), including profiles/roles:

- `profiles` + `profile_permissions` + `profile_approvals` (roles and access, editable in UI)
- `tracks` N–M `profiles` via `track_profiles`
- `tasks` (title, description, category, due_date, **follow_up**: twice_daily / daily /
  weekly / biweekly — how often the AI chases it, est_hours, link, evidence_required,
  requires_approval, sort) 1–N `task_contacts` ("Juan already took this course")
- `people` 1–N `person_tasks` (status, evidence, progress_note, timestamps)
  and 1–N `check_ins` (AM/PM journal)

Dummy data ships as an idempotent seed migration (`bench/seed.py`); `seed_if_empty()`
runs on app startup. Verification (`verify_progress`) derives everything from rows:
which tasks are due for follow-up today, freshness, missing evidence, deadline risk.

The workshop's onboarding domain (`agent/`, `profiles/*.yaml`, `projects/*.yaml`)
keeps its YAML — that material belongs to `main`.

## Consequences

- The UI edits real entities (add task, add role) instead of raw text; no YAML parsing errors.
- Catalog changes are no longer reviewed via git; acceptable for dev, revisit for
  access-definition changes in production (audit trail moves to the DB / DynamoDB streams).
- The DynamoDB migration path is table-per-table instead of file-per-file; function
  signatures in `bench/tools/` remain the swap seam.
