---
baseline_commit: 92b59f23c89e8650513df7718c86f1dabf5b4a8e
---

# Story 1.1: Version the Bench schema and backfill durable identity and lifecycle fields

Status: review

## Story

As a Bench operator,
I want existing Bench databases upgraded through explicit versioned migrations,
so that lifecycle, stable identity, and history fields are available without silently losing data.

## Acceptance Criteria

1. Given an existing database at each supported pre-migration schema version, when the application opens it, then migrations run in version order, are recorded, and are idempotent.
2. The migration path introduces only the fields owned by this story: stable `person_id`, normalized/editable email support, explicit lifecycle/archive state, and task active/archive state needed by people and task-history stories. Audit storage belongs to Story 1.3; report metadata to Story 3.2; notification projection fields to Story 3.3.
3. Existing people receive deterministic, non-empty stable identities. All person-owned historical rows remain associated with the same person after backfill, including `person_tasks`, `check_ins`, `conversation_refs`, and existing notification rows; do not delete local history automatically.
4. Duplicate person identities and case-insensitive responsible conflicts encountered during backfill fail closed with an actionable conflict error. The migration must not silently merge, invent a winner, or partially commit the backfill.
5. A person email can later be changed without changing the stable `person_id` used to resolve historical references. Email input is normalized consistently with the existing API behavior (trimmed and lower-cased) while preserving the canonical user-facing value required by the project.
6. Existing task templates remain distinct from person task instances. A task has an explicit active/archive representation for later history-safe catalog behavior, while this story does not implement task deletion policy or rewrite instantiated task history.
7. Running the migration twice produces the same schema and data state, and opening a current database does not reapply or corrupt prior migrations.
8. Existing Bench behavior remains green after the schema upgrade. `uv run pytest` is the documented validation command; migration-specific tests cover old schemas, current schemas, repeat upgrades, successful backfills, conflict failures, stable identity, and historical-row preservation.

## Tasks / Subtasks

- [x] Inspect the current schema and enumerate every person-keyed relationship before changing ownership (AC: 2, 3, 5)
  - [x] Capture the current `people.email` primary-key model and references in `person_tasks`, `check_ins`, `conversation_refs`, and `notifications`.
  - [x] Define the supported pre-migration schema versions and the persisted migration-version mechanism.
  - [x] Keep the migration boundary explicit so audit/report/notification redesign remains in its later stories.
- [x] Replace ad-hoc connect-time column additions with ordered, idempotent migrations (AC: 1, 2, 7)
  - [x] Preserve fresh-database creation and current seeded catalog behavior.
  - [x] Apply migrations transactionally where SQLite permits and record a migration only after its changes succeed.
  - [x] Make the migration runner safe for repeated `connect()` calls and current databases.
- [x] Backfill stable person identity and editable normalized email support (AC: 3, 4, 5)
  - [x] Generate deterministic stable identities for existing people without using mutable email as the durable identity.
  - [x] Validate duplicate normalized identities before committing any backfill.
  - [x] Preserve foreign-key/history meaning while moving lookups toward `person_id`; do not use destructive delete-and-reinsert shortcuts.
- [x] Add explicit lifecycle/archive and task active/archive fields (AC: 2, 6)
  - [x] Keep derived date lifecycle values (`inactive`, `pre_bench`, `active`) separate from archive state.
  - [x] Use defaults that preserve current active behavior for existing records.
  - [x] Do not implement archive/restore UI or task deletion in this story.
- [x] Add migration regression coverage (AC: 1, 3, 4, 5, 7, 8)
  - [x] Build fixtures for each supported legacy schema and a current schema.
  - [x] Assert successful backfill, repeatability, stable IDs, normalized email validation, and every historical reference remaining attributable.
  - [x] Assert duplicate people/responsible conflicts fail closed and leave the database unchanged or safely recoverable.
  - [x] Run the full suite with `uv run pytest`.

## Dev Notes

### Scope and non-goals

This is the first story in the six-step foundation sequence. It establishes the schema/migration substrate only. Do not implement actor resolution/audit records (Story 1.2/1.3), including the ratified `BENCH_ACTOR` source and visible `local-operator` fallback; report records (Story 3.2); notification lifecycle projections (Story 3.3); people UI/archive/restore (Epic 2); or catalog deletion behavior (Epic 4). Do not modify requirements, UX, architecture, ADR, or test documents outside the implementation work required by this story.

SQLite remains authoritative for Bench local state. Rendered Markdown and UI state are projections. Bench remains isolated from the onboarding YAML domain, and the existing Strands/LangGraph boundaries remain unchanged.

### Current implementation findings

- `bench/db.py` currently creates the full schema from `_SCHEMA` and applies `_MIGRATIONS` as untracked `ALTER TABLE people ADD COLUMN ...` statements, swallowing every `sqlite3.OperationalError` as if it meant “column already exists.” Replace this with an explicit versioned migration mechanism rather than extending the current exception-swallowing list.
- `people.email` is currently the primary key and is used by existing state tools and historical tables. An email edit must not orphan or rewrite historical records. Inspect and update all affected queries/contracts coherently; do not patch only `bench/db.py`.
- `bench/tools/state.py` currently uses email for person lookup and `start_bench()` deletes existing `check_ins` and `person_tasks` before replacing a person. That reset behavior is outside this story but must not be made worse by the migration. Preserve current tests while leaving the later history-safety changes for Epic 2.
- `bench/tools/catalog.py` currently treats `tasks` as templates and `person_tasks` as instances. Preserve this separation. Its current `delete_task()` deletes instances and is a later Epic 2/4 change, not an excuse to implement catalog policy here.
- `bench/api.py` already normalizes incoming employee emails with `_email_key()` (`strip().lower()`). Reuse or centralize that rule rather than introducing a conflicting normalization policy.

### Ratified architecture guardrails

- AD-1/AD-2: Bench is a parallel domain; SQLite is the single local source of truth.
- AD-3: Catalog task templates and per-person task instances remain separate.
- AD-8: Archive/lifecycle state is distinct from date-derived `inactive`, `pre_bench`, and `active` status.
- AD-13: Archived people remain dependencies; local history has no automatic retention deletion.
- AD-15: Keep schema details behind `bench/db.py` and domain-shaped tool seams so a future storage adapter does not leak SQLite details into channels.

Required preservation locks: stable `person_id` is the durable identity; email is editable and normalized; no automatic history deletion; instantiated task identity remains attributable; approval vocabulary, actor behavior, report/notification projection separation, and localhost-only trust boundary must remain unchanged for later stories.

### Migration design constraints

- Prefer a small migration registry/table with monotonically ordered versions and explicit upgrade functions. A migration must be discoverable, testable, and applied only when its version is absent.
- Treat conflict validation as a precondition for the migration that mutates identity/reference data. On conflict, fail with an actionable message containing enough information to resolve the duplicate, and do not mark the migration complete.
- Do not rely on catching broad `OperationalError` to infer migration state. Distinguish an already-applied migration from malformed schema, foreign-key failure, or another operational defect.
- Make transaction boundaries explicit. Python `sqlite3.executescript()` has transaction behavior that can surprise callers, so do not assume a surrounding transaction remains open across it; use explicit statements/transactions consistent with the repository’s connection context.
- Preserve foreign keys (`PRAGMA foreign_keys = ON`) and verify them after migration. If a table rebuild is needed for SQLite constraints, copy rows explicitly and verify counts/references before commit.
- Use parameterized SQL for all data values. Never build SQL from emails, names, or other user-controlled strings.
- Do not use timestamps or mutable emails as the only stable identity source. The identity must be deterministic for the same legacy row and remain unchanged after email edits.

### Expected implementation areas

Likely files to inspect/update:

- `bench/db.py` — migration registry/runner, schema definitions, connection initialization, stable identity/lifecycle/task fields.
- `tests/test_bench.py` — migration fixtures and regression coverage; preserve existing seeded state tests.
- `tests/test_api.py` and other existing tests — update only if the stable identity contract necessarily changes an existing observable behavior.

Do not create a second database layer or put migration logic in `bench/webapp.py`, `bench/api.py`, `bench/tools/state.py`, or templates. If a compatibility lookup is needed, keep it in the shared storage/tool seam and cover it with tests.

### Testing requirements

Migration tests must use isolated temporary SQLite databases and exercise at least:

- fresh database creation;
- every supported legacy schema version;
- current database no-op/reopen;
- repeated migration execution;
- existing people backfilled with stable identities;
- email normalization/edit preserving `person_id` and historical references;
- `person_tasks`, `check_ins`, `conversation_refs`, and notifications retained;
- duplicate normalized person identity conflict;
- case-insensitive responsible conflict;
- rollback/no partial migration after a conflict;
- active/archive defaults and task active/archive defaults;
- current application regression suite.

The canonical project contract names `python -m pytest --version` and `python -m pytest`; this worktree’s documented command is `uv run pytest`, which must be used for the implementation validation and reported with its real result. Missing pytest is an environment defect, not a waived test result.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-1-Durable-foundation-and-mutation-audit]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1-Version-the-Bench-schema-and-backfill-durable-identity-and-lifecycle-fields]
- [Source: docs/spec-review-dayone-bench-ui/SPEC.md#Constraints]
- [Source: docs/spec-review-dayone-bench-ui/SPEC.md#CAP-1--Shared-durable-mutation-foundation]
- [Source: docs/spec-review-dayone-bench-ui/items-must-not-change.md]
- [Source: docs/spec-review-dayone-bench-ui/current-state-gap-matrix.md#Migrationhistory-policy]
- [Source: docs/spec-review-dayone-bench-ui/epic-story-implications.md#Epic-1--Durable-foundation-and-mutation-audit]
- [Source: docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md#AD-2--SQLite-owns-local-Bench-truth]
- [Source: docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md#AD-8--Person-lifecycle-is-explicit-and-distinct-from-date-status]
- [Source: docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md#AD-15--Storage-replacement-is-behind-the-tool-seam]
- [SQLite ALTER TABLE documentation](https://sqlite.org/lang_altertable.html)
- [Python sqlite3 transaction documentation](https://docs.python.org/3/library/sqlite3.html#transaction-control)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Initial targeted migration tests failed because the versioned migration runner and durable identity columns did not yet exist; implemented the runner and reran them successfully.
- Email-edit regression initially hit legacy foreign-key enforcement; corrected it with an atomic compatibility-key rotation and `PRAGMA foreign_key_check` verification.

### Implementation Plan

- Replace swallowed connect-time `ALTER TABLE` statements with three ordered migrations recorded in `schema_migrations`.
- Backfill deterministic UUID5 person identities, normalized email keys, durable history links, and archive defaults after validating person/responsible conflicts.
- Keep legacy email columns and existing tool contracts compatible while new writes populate `person_id`; expose an atomic email-update seam that preserves history.
- Cover legacy/current/repeat/conflict/email-edit paths and run the complete `uv run pytest` suite.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added transactional, ordered schema migrations with repeat-safe version recording.
- Backfilled deterministic `person_id` values and durable links for people, tasks, check-ins, conversation references, and person-owned notifications.
- Added normalized/editable email support, conflict fail-closed validation, separate people/task archive flags, and compatibility writes for new records.
- Added migration regression coverage for backfill, history preservation, idempotency, email edits, and responsible/person conflicts.
- Senior review fixes: durable links for knowledge-materialized tasks, normalized person-ID state lookups, and safe unknown-person notification handling.
- Validation: `uv run pytest` → 23 passed, 2 skipped; `git diff --check` passed.

### File List

- `_bmad-output/implementation-artifacts/1-1-version-the-bench-schema-and-backfill-durable-identity-and-lifecycle-fields.md`
- `bench/db.py`
- `bench/notify.py`
- `bench/tools/catalog.py`
- `bench/tools/state.py`
- `tests/test_bench.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-07-21: Implemented versioned schema migrations, durable identity/history backfill, lifecycle/archive fields, normalized email editing, and regression tests; status advanced to review.
- 2026-07-21: Completed senior code review; fixed three durable-identity and notification-safety findings and expanded regression coverage.
