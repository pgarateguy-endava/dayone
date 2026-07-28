---
baseline_commit: a1bea6d
---

# Story 1.3: Audit shared mutations atomically and expose action history queries

Status: done

> **Non-negotiable storage invariant:** A Bench runtime selects exactly one authoritative data source. SQLite mode uses SQLite exclusively; DynamoDB mode uses DynamoDB exclusively. No hybrid table routing, mirrored writes, read fallback, or cross-source reconciliation is allowed. DynamoDB schema and behavior parity are deferred to a follow-up epic/story; Story 1.3 implements and validates the audit foundation in SQLite mode only.

## Story

As an operator,
I want mutation outcomes recorded with actor and target context,
so that lifecycle and catalog changes can be explained after the fact.

## Acceptance Criteria

1. **Successful mutations are auditable and atomic.** Given a supported create, edit, archive/delete, status/date, approval-display, report, or notification mutation succeeds, when the transaction commits, then exactly one append-only audit record stores the resolved actor, UTC timestamp, entity type, entity ID, action, outcome, and target/detail context in the same SQLite transaction where possible, and the returned projection reflects committed SQLite state.
2. **Rejected mutations preserve the original error.** Given a mutation is rejected, when an error is returned, then the actionable original error remains intact; a rejected audit outcome is recorded only when it can be persisted without masking or replacing that error. A failed mutation must not leave its durable state or success audit row committed.
3. **History queries are stable and person-scoped.** Given an employee detail/action-history query, when history is requested for a stable `person_id`, then records for that person are returned in deterministic newest-first order with enough entity/action/outcome/context data for an operator to explain the change. Email changes must not detach prior records from the person.
4. **The shared seam is channel-independent and append-only.** Given the same domain mutation is invoked through web, API, CLI, Teams-facing, or scheduled paths, when it writes through shared Bench tools, then actor and audit behavior are consistent; no route, template, generated text, or channel-local identity writes audit records directly. The exposed audit API provides append/list behavior only; there is no update/delete operation for audit history.
5. **Existing behavior remains intact.** Given current onboarding, task/check-in, catalog, notification, report, actor-boundary, migration, and DynamoDB-adapter tests, when the story changes are applied, then existing deterministic state transitions and storage boundaries continue to work, and no local task, report, notification, check-in, conversation, or other history is deleted merely because auditing was added.

## Tasks / Subtasks

- [x] Add a versioned SQLite audit schema and migration (AC: 1, 2, 3, 5)
  - [x] Add an append-only `audit_log` table with generated row identity, UTC timestamp, actor, entity type, nullable/entity-specific ID, action, outcome, and serialized target/detail context; add indexes supporting deterministic global and `person_id` history queries.
  - [x] Keep migration ordering/idempotency and fail-closed behavior consistent with `schema_migrations`; do not rewrite prior migrations or silently backfill invented audit history.
  - [x] Confirm foreign-key/identity behavior and preserve existing rows on migration failure or rollback.
- [x] Implement the shared audit tool contract (AC: 1, 3, 4)
  - [x] Add `bench/tools/audit.py` (or the nearest existing tool seam) with connection-aware append and list/query helpers so a caller can append using its active transaction rather than opening a second connection.
  - [x] Resolve the actor through `bench.actor.current_actor()` / established boundary rules; never use API tokens, employee email, hard-coded channel names, or `None` as an audit actor.
  - [x] Normalize/serialize context deterministically, avoid storing secrets or full report/file contents, and return plain dictionaries suitable for API/UI projections.
  - [x] Define deterministic ordering, preferably timestamp plus monotonic audit ID, and stable filters for `person_id`, entity type/ID, action, outcome, and limit.
- [x] Instrument shared SQLite mutations without changing their domain contracts (AC: 1, 2, 4, 5)
  - [x] Use one connection/transaction for the durable mutation plus its successful audit row; do not append after the connection has committed.
  - [x] Cover current write tools in `bench/tools/state.py`, `bench/tools/catalog.py`, `bench/tools/knowledge.py`, `bench/db.py`, and notification/report paths in `bench/notify.py`/`bench/graph.py` as applicable to this repository.
  - [x] Include reset/clear operations and protected/rejected mutations in the audit decision: destructive local behavior cannot become invisible, but an audit-write failure must not replace the domain error.
  - [x] Preserve existing return shapes, exception types/messages, actor context boundaries, SQLite default, and future storage-adapter seam. Do not implement hosted auth, real notification delivery, DynamoDB audit storage, or a new UI in this story.
  - [x] Treat backend selection as runtime-wide and exclusive. Do not add per-table backend decisions, mixed reads, mirrored writes, fallback reads, or cross-source reconciliation.
- [x] Record the deferred DynamoDB parity boundary (AC: 5)
  - [x] Keep Story 1.3's implementation and acceptance tests on SQLite as the authoritative source; preserve the existing DynamoDB compatibility tests without presenting the current partial adapter as a complete backend.
  - [x] Leave complete DynamoDB schema/behavior synchronization to a follow-up epic/story covering the full Bench domain, stable identity, audit/history, reports/notifications, migrations, consistency, idempotency, and parity tests before DynamoDB-only mode is enabled.
- [x] Expose person action history through the existing domain/web projection seams (AC: 3, 4)
  - [x] Add a read helper that accepts stable `person_id`; use email only for compatibility lookup, never as the durable scope.
  - [x] Expose the domain query seam for the later UI story; no existing action-history placeholder required a new visual projection in this foundation story.
  - [x] Keep the query helper projection-safe by returning structured values; no route/template audit SQL or business rules were added.
- [x] Add focused regression and transaction tests (AC: 1–5)
  - [x] Test schema creation/migration idempotency and indexes.
  - [x] Test successful mutation + audit commit, rollback coupling, rejected mutation preservation, append-only behavior, required actor/fields, and deterministic ordering.
  - [x] Test person-scoped history before/after email change and entity IDs for representative task/person operations.
  - [x] Preserve actor-boundary coverage and keep the full existing suite green, including DynamoDB compatibility tests.

### Review Findings

- [x] [Review][Patch] Add an outbox/reconciliation protocol for report persistence and audit — `save_eod_report()` writes to local disk/S3 before the SQLite audit transaction; if auditing fails, the report remains durable but unaudited while the operation raises. Implement the selected outbox/reconciliation approach. [bench/tools/eod_report.py:76-87]
- [x] [Review][Patch] Keep mandatory-task materialization and completion audit-atomic — `mark_task_done_by_title()` can commit a newly materialized task/person assignment before `update_task_status()` runs in a separate transaction, leaving durable unaudited state if the second step fails. [bench/tools/state.py:263-275]
- [x] [Review][Patch] Couple date changes with notification clearing — `set_bench_start_date()` commits the date and audit before `clear_notifications()` runs separately, so a clear failure leaves a partially applied mutation. [bench/tools/state.py:316-333; bench/notify.py:272-282]
- [x] [Review][Patch] Do not record success for missing catalog or knowledge targets — update/delete paths append `succeeded` rows even when `rowcount` is zero, claiming a mutation that changed no state. [bench/tools/catalog.py:142-178,197-239; bench/tools/knowledge.py:44-57]
- [x] [Review][Patch] Preserve person scope for catalog fan-out mutations — task creation/deletion can affect multiple `person_tasks`, but the single catalog audit row has no `person_id`, so employee history cannot explain those changes. [bench/tools/catalog.py:90-95,158-164,206-222]
- [x] [Review][Patch] Enforce service-generated audit metadata — `append_audit()` accepts caller-supplied timestamps and unnormalized field values, allowing forged ordering and inconsistent filters contrary to the audit contract. [bench/tools/audit.py:13-37]
- [x] [Review][Defer] Complete DynamoDB backend exclusivity and audit/history parity — the current selector still routes notification/conversation data to DynamoDB while people/catalog/history remain SQLite. This is pre-existing transitional behavior explicitly deferred by Story 1.3 and must be resolved before DynamoDB-only mode is enabled. [bench/config.py:30-33; bench/notify.py:46-118; bench/tools/audit.py:42-70] — deferred, pre-existing

### Review Findings — second pass

- [x] [Review][Patch] Propagate email identity changes into report outbox rows — `update_person_email()` updates existing email-bearing tables but not `report_outbox`, leaving queued reports under stale employee identity. [bench/db.py:611-614]
- [x] [Review][Patch] Return the persisted task-status projection — when evidence or note is blank, SQL preserves the existing value but the returned dictionary reports the blank input instead of committed state. [bench/tools/state.py:139-155]
- [x] [Review][Patch] Explain destructive re-onboarding resets — `start_bench()` deletes prior check-ins and task instances, but the audit context omits reset counts and affected scope. [bench/tools/state.py:62-90]
- [x] [Review][Patch] Add person scope to catalog updates and cascades — `update_task()`, `update_track()`, and track cascades affect person-linked records without including affected person IDs and bounded target details in audit context. [bench/tools/catalog.py:145-160,206-243]
- [x] [Review][Patch] Make notification delivery idempotent — repeated `mark_delivered()` calls overwrite an already-delivered row and append duplicate success audits. [bench/notify.py:251-263]
- [x] [Review][Patch] Constrain audit context and tolerate malformed legacy JSON — caller context is unbounded and may contain secrets or oversized payloads, while history queries fail completely on invalid stored JSON. [bench/tools/audit.py:21-35,61-80; bench/db.py:482-492]
- [x] [Review][Patch] Require a known person for report history — report saves currently allow `person_id = NULL`, making completed reports invisible to person-scoped history. [bench/tools/eod_report.py:81-94]
- [x] [Review][Defer] DynamoDB date/notification atomicity — DynamoDB mode still updates SQLite person/audit state before clearing DynamoDB notifications; this is part of the pre-existing transitional backend and remains deferred with full parity. [bench/tools/state.py:321-339] — deferred, pre-existing

## Dev Notes

### Story foundation and scope

This is the third foundation story. Story 1.1 provides stable `person_id`, normalized email, lifecycle/archive fields, and history links. Story 1.2 provides `BENCH_ACTOR`, visible `local-operator` fallback, and scoped actor boundaries. Build on both; do not reimplement identity or actor resolution.

The canonical contract is the ratified local SQLite UI SPEC. SQLite is authoritative for Bench facts; audit history is an append-only domain record, not rendered Markdown and not an LLM-generated explanation. Later stories consume this query seam for employee detail, catalog safety, reports, and notification projections.

### Current implementation intelligence

- `bench/db.py` owns `_SCHEMA`, versioned migrations 1–4, `connect()`, and stable identity/email migration helpers. `connect()` enables foreign keys and returns a row-factory connection; `with connect() as conn` commits on success and rolls back on exception. Add the next migration rather than modifying old migration semantics.
- `bench/actor.py` owns environment/scoped actor resolution. `bench/webapp.py`, `bench/api.py`, CLI entry points, LangGraph, and agent paths establish actor boundaries. Preserve the rule that a boundary resolves from the environment and does not inherit an unrelated scoped test actor.
- `bench/tools/state.py` owns person task/check-in/date mutations. `start_bench()` currently resets check-ins and person tasks for an existing person before re-instantiation; this is a high-risk mutation that must be intentionally audited and must not be expanded into broad history deletion.
- `bench/tools/catalog.py` owns profile/track/task/responsible writes. Existing `delete_task()` removes person-task instances, and `delete_track()` removes related tasks/instances; this story must not silently redesign those history policies, but must make the actual supported mutation outcome visible and preserve the SPEC boundary for later history-safety work.
- `bench/tools/knowledge.py` owns knowledge CRUD. `bench/notify.py` owns conversation refs, queue/delivery/clear operations, and notification logs; local SQLite notification state is distinct from the DynamoDB adapter in `bench/dynamo.py`.
- `bench/webapp.py` is a large single-module FastAPI/HTML projection with existing routes for people, tasks, check-ins, catalog, reports, and notifications. Keep SQL out of new route logic; use the tool seam and existing escaping helpers. Do not refactor unrelated UI during this foundation story.

### ⚠️ DynamoDB integration impact — explicit exclusive-source boundary

The AWS integration already exists on the story branch, but its current implementation is partial and does not yet satisfy the exclusive-source invariant:

- `BENCH_STORAGE=dynamodb` currently routes only per-person `conversation_refs` and `notifications` through `bench/dynamo.py`, while catalog, `people`, `person_tasks`, check-ins, and the current SQLite schema remain local SQLite. That is a **known transitional hybrid**, not the target architecture and not a valid complete DynamoDB-only mode. The default remains SQLite.
- The target behavior is mutually exclusive: one runtime chooses SQLite for all Bench data or DynamoDB for all Bench data. The selector must not silently choose DynamoDB for one table family and SQLite for another.
- DynamoDB records currently use `email` as the conversation key and a UUID string as the notification key; they do not carry the durable SQLite `person_id`. Email edits therefore must not be assumed to migrate or re-key remote notification/conversation history in this story.
- DynamoDB calls use separate `put_item`, `update_item`, and `delete_item` operations and have no cross-store transaction with SQLite. Do **not** write a SQLite audit row after a DynamoDB call and describe that pair as atomic. Do **not** add a second `audit_log` table/key design to DynamoDB here: the architecture explicitly defers DynamoDB table/key design and migration execution.
- For this story, the atomic audit guarantee applies only to the SQLite implementation. The existing partial DynamoDB adapter remains a compatibility baseline and must not be expanded, mixed with SQLite, or treated as satisfying the complete audit contract.
- Complete DynamoDB schema and behavior synchronization is a follow-up epic/story. That work must define the full schema, stable identity, audit/history, reports/notifications, migrations, consistency, idempotency, and all-backend parity tests before enabling DynamoDB-only runtime mode.
- Add/retain isolated compatibility tests with `BENCH_STORAGE=dynamodb` for the current adapter, but do not require live AWS credentials in the normal suite and do not use those tests to authorize hybrid production behavior.

### Required audit contract

Use a stable, documented vocabulary for fields:

| Field | Requirement |
|---|---|
| `id` | Monotonic SQLite row identity used as the final deterministic ordering key. |
| `at` | UTC ISO-8601 timestamp generated by the service, not browser/client time. |
| `actor` | Non-blank `current_actor()` value, including `local-operator` fallback. |
| `entity_type` / `entity_id` | Domain target such as `person`, `person_task`, `track`, `task`, `notification`; preserve stable person identity where applicable. |
| `action` | Verb-led, stable operation name; do not derive it from UI labels or generated prose. |
| `outcome` | At minimum `succeeded` and `rejected`; use a consistent failure vocabulary if the implementation needs an additional non-success state. |
| `context` | JSON/text object with safe target/detail context; deterministic serialization, no credentials/tokens/secrets or report body. |

For person history, a person mutation uses `entity_id = person_id`; a related task/check-in/report/notification audit record includes the same `person_id` in context or an explicit person scope column/index so email edits do not break queries. Query ordering must not depend on lexical timestamps alone.

The audit helper should accept an existing `sqlite3.Connection` (or an equivalent explicit transaction object) for writes. A helper that calls `connect()` internally from inside a mutation would create a second transaction and violate atomicity. Reads may use their own connection after commit.

### Architecture compliance

- AD-1/AD-2: SQLite is the local source of truth; schema details stay in `bench/db.py` and shared tools.
- AD-4/AD-5: deterministic writes remain authoritative; generated plans/reports/chat are read-only projections of stored facts.
- AD-8: stable person identity and archive/lifecycle are separate; history queries must remain person-scoped even when email changes or a person is archived.
- AD-9: every in-scope mutation has explicit actor, timestamp, entity, action, outcome, and context; success audit is transaction-coupled where possible; rejected audit never masks the original error.
- AD-10: report save and notification status remain separate; audit their distinct operations rather than collapsing them into “sent”.
- AD-15: the operation contract must be usable by web/API/Teams/CLI/scheduled paths and must not expose SQLite-only assumptions to a future adapter.
- Storage exclusivity: the adapter seam selects one complete backend for a runtime. The current partial DynamoDB implementation is transitional and must be synchronized in a follow-up epic/story before it can replace SQLite; it must never cause a hybrid runtime.

### File and structure guardrails

Expected primary files (confirm names against the current tree before implementation):

- UPDATE `bench/db.py`: audit schema and migration/index registration.
- NEW `bench/tools/audit.py` or the existing nearest shared-tool module: append/list/query contract.
- UPDATE `bench/tools/state.py`, `bench/tools/catalog.py`, `bench/tools/knowledge.py`, `bench/notify.py`, and any report mutation owner identified by code search: use the active connection and append exactly one success audit per supported mutation.
- UPDATE only the smallest necessary portions of `bench/webapp.py`/`bench/api.py`: consume the tool query/projection; do not put audit SQL or business rules in routes.
- NEW/UPDATE focused tests, preferably `tests/test_audit.py` plus existing `tests/test_bench.py`, `tests/test_notify.py`, `tests/test_api.py`, and `tests/test_webapp.py` where boundary coverage belongs.

Do not modify `docs/` requirements, UX, architecture, ADR, or test documents as part of implementation without explicit authorization. Do not add dependencies; the current stack is Python stdlib `sqlite3`, FastAPI/Starlette, htmx, and pytest through the repository's existing `uv` environment.

### Testing requirements

Use the child repository's canonical commands:

```bash
uv run pytest
```

Also run focused audit tests while iterating. Tests must use isolated temporary `PROGRESS_DIR`/SQLite databases, must not rely on developer-local `.local-progress`, and must assert actual persisted rows after reopening a connection. Include forced audit failure/rollback tests without swallowing the original exception. The story is not complete if pytest is unavailable; that is an environment defect.

### Previous story intelligence

Story 1.2 established `bench.actor.actor_context()` and `current_actor()` with tests for configured values, blank fallback, nested restoration, exception restoration, async isolation, and boundary non-inheritance. Its implementation touched actor boundaries in web/API/CLI/LangGraph/agent paths. Reuse those seams and add audit assertions; do not pass channel actor values through new parameters or let a test override leak between calls.

### Git intelligence

Recent commits `f3e3e14` and `75419be` added and hardened Story 1.2. They favor small shared helpers, environment-derived actor boundaries, explicit tests, and no new framework. The current branch already contains Story 1.1 migration work and Story 1.2 actor work; inspect the exact current code before editing because this story must build on those merged commits.

### Latest technical specifics

- Python 3.14 documentation states that a `sqlite3.Connection` context manager commits on normal exit and rolls back on exception, but the connection still needs explicit closing. This matches the repository's `with connect() as conn` pattern; keep mutation and audit insert in that same context. Source: https://docs.python.org/3/library/sqlite3.html
- SQLite remains the transactional local store; use parameterized SQL and the existing migration mechanism. Source: https://sqlite.org/docs.html
- htmx targets and swaps are response-projection concerns: `hx-target` selects the element and `hx-swap` controls replacement. Audit persistence must complete server-side before any fragment is returned; do not use optimistic client state. Sources: https://htmx.org/docs/, https://htmx.org/attributes/hx-target/, https://htmx.org/attributes/hx-swap/
- The current DynamoDB adapter creates on-demand tables using `BENCH_DYNAMODB_PREFIX`, uses `AWS_REGION`, and treats missing tables as empty on read. These are existing adapter behaviors to preserve, not new Story 1.3 requirements. Source: `bench/dynamo.py`, `tests/test_dynamo.py`, `docs/ROADMAP.md`.
- The current `BENCH_STORAGE=dynamodb` path is intentionally incomplete: its tests document that catalog and people remain in SQLite. Treat that as a migration gap to be resolved by a follow-up epic/story, not as a design pattern to extend. Source: `bench/config.py`, `bench/dynamo.py`, `tests/test_dynamo.py`, `docs/ROADMAP.md`.

### Project context reference

Follow the project facts in `docs/development-workflow.md`, `docs/ARCHITECTURE.md`, `docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md`, and `docs/spec-review-dayone-bench-ui/SPEC.md`. Preserve the canonical six-step foundation sequence, the localhost trust boundary, SQLite authority, shared `bench/tools` ownership, explicit actor fallback, and no-credentials rule.

### Completion notes

Ultimate context engine analysis completed - comprehensive developer guide created. Story is ready for implementation in its dedicated worktree; implementation, test execution, code review, commit, push, and PR creation are separate workflow steps.

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Focused audit/migration tests: `uv run pytest tests/test_audit.py tests/test_bench.py -q` — 21 passed.
- Final focused audit tests: `uv run pytest tests/test_audit.py -q` — 6 passed.
- Full regression suite: `uv run pytest -q` — 45 passed, 2 skipped.

### Completion Notes List

- Story context created from the canonical Epic 1.3 contract, Story 1.2 learnings, current source tree, architecture/UX/SPEC constraints, Git history, and primary technical documentation.
- Added SQLite migration 5 with append-only audit triggers and indexed history queries.
- Instrumented shared SQLite state, catalog, knowledge, identity, notification, and report mutations with transaction-coupled success audits while leaving DynamoDB adapter behavior unchanged.
- Explicitly preserved the exclusive-backend boundary: DynamoDB schema and behavior parity remains deferred to a follow-up story/epic.
- Adversarial code review resolved six patch findings, including report outbox reconciliation, composite mutation rollback coupling, no-op audit suppression, person-scoped catalog context, and generated audit metadata validation.
- Code review deferred the pre-existing partial DynamoDB hybrid until the dedicated backend parity work.
- Second-pass review resolved seven additional findings and retained DynamoDB date/notification atomicity as deferred pre-existing parity work.

### File List

- `_bmad-output/implementation-artifacts/1-3-audit-shared-mutations-atomically-and-expose-action-history-queries.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `bench/db.py`
- `bench/notify.py`
- `bench/tools/audit.py`
- `bench/tools/catalog.py`
- `bench/tools/eod_report.py`
- `bench/tools/knowledge.py`
- `bench/tools/state.py`
- `tests/test_audit.py`
- `tests/test_bench.py`
