# Proposed epic/story implications

Stories must be ordered by the foundation sequence and must not split shared seams into channel-specific fixes.

## Epic 1 — Durable foundation and mutation audit

- Schema/migration story: lifecycle/archive, task active/archive identity, audit, report index, and notification projection records.
- Shared context story: resolve `BENCH_ACTOR` with visible fallback and propagate it through web, API, Teams, CLI, and scheduled calls.
- Audit story: record actor/time/entity/action/outcome/context in the same transaction where possible; expose read queries.
- Regression story: verify SQLite source of truth and stable tool-shaped contracts.

## Epic 2 — People lifecycle and history safety

- People edit story: name, email, profile, track, date, and profile context with validation and identity rules.
- Archive/restore story: archive-only UI removal, active/archived views, restore, confirmation, and retained history.
- Task-history story: replace destructive instantiated-task deletion and protect historical report/task identity.
- Date-evaluation story: save date changes and immediately re-evaluate lifecycle notifications with audit records.

## Epic 3 — Responsibles and status projections

- Responsible CRUD story: update/remove/add, case-insensitive per-track uniqueness, cross-track reuse, audit.
- Report projection story: durable local report record, recipient metadata, read-only content, save status.
- Notification projection story: independent pending/queued/delivered/error status and delivery timestamps.
- Approval projection story: render only the three ratified simulated states with non-granting copy.

## Epic 4 — Navigation and remaining catalog CRUD

- Persistent navigation story: Tracks link, active location, keyboard visibility, and documented parent routes.
- Track detail story: task/responsible ownership, independent saves, protected role/track deletion feedback.
- Catalog consistency story: role/track/task/knowledge mutations use shared tools, confirmation, escaping, and audit.

## Epic 5 — Accessibility and responsive behavior

- Dialog/form semantics story: names, labels, required/help text, focus movement/trap/return, Cancel safety.
- Dynamic feedback story: stable htmx targets, associated validation, announced success/error, focus preservation.
- Table/navigation story: accessible row actions, active nav, text-plus-color states, 200% zoom, narrow-screen scrolling/menu.

## Epic 6 — Verification and acceptance

- Unit/API stories for schema, lifecycle, audit, uniqueness, task safety, status projections, and actor override.
- UI/E2E stories for every UI-FR and protected deletion/date-change flow.
- Accessibility/regression story for markup and keyboard-oriented acceptance.
- Environment story: make executable `pytest` a development prerequisite, fail setup/validation when it is absent, and record the complete suite from an actual run; do not backfill results from this proposal.
- Test-matrix story: map UI-FR-001 through UI-FR-013 to named automated or manual acceptance scenarios and maintain the map through implementation.
- Migration/operations story: version schema upgrades, define conflict handling, and document indefinite local history plus manual reset/backup procedures.
