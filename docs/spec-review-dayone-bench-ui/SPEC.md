---
id: SPEC-dayone-bench-ui
companions:
  - change-summary.md
  - current-state-gap-matrix.md
  - traceability.md
  - epic-story-implications.md
  - approval-checklist.md
  - items-must-not-change.md
  - ../ux-dayone-bench/DESIGN.md
  - ../ux-dayone-bench/EXPERIENCE.md
  - ../architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md
sources:
  - ../PRODUCT_SPEC.md
  - ../BACKOFFICE_SPEC.md
  - ../ROADMAP.md
  - ../BENCH_SPEC.md
  - ../ARCHITECTURE.md
  - ../adr/0001-bench-as-parallel-domain.md
  - ../adr/0002-hybrid-strands-langgraph.md
  - ../adr/0003-relational-catalog-sqlite.md
  - ../adr/0004-teams-bot-thin-channel.md
---

> **Canonical target contract.** This proposal describes what the DayOne Bench local UI must become. It is not evidence that the implementation already satisfies the contract.

# DayOne Bench UI completion

## Why

The local Bench operator surface already demonstrates core onboarding, catalog, progress, report, and notification flows, but its lifecycle and mutation seams are incomplete. Managers, People Leads, enablement operators, and Bench engineers need a discoverable, safe, auditable UI whose displayed state remains grounded in SQLite and deterministic tools. This contract closes the missing seams before story planning while preserving the approved localhost MVP boundary.

## Capabilities

- **CAP-1 — Shared durable mutation foundation**
  - **intent:** The system can persist lifecycle, audit, report, notification, and approval-projection facts through shared domain seams used by every channel.
  - **success:** Each in-scope mutation commits its durable fact and actor context in SQLite, and the UI/API/Teams/CLI/scheduled paths can retrieve the same result without route-owned business logic.

- **CAP-2 — Safe people lifecycle**
  - **intent:** An operator can edit, archive, restore, and inspect people without losing their instantiated task history, check-ins, reports, notifications, or audit history.
  - **success:** Active views exclude archived people by default; archived views expose restore and history; archive is the only UI removal action; edits and date changes preserve identity and trigger immediate lifecycle evaluation where applicable.

- **CAP-3 — History-safe task catalog**
  - **intent:** An operator can maintain task templates while preserving the identity and state of instantiated person tasks.
  - **success:** A pre-instantiation task can be physically deleted; an instantiated task is archived/inactivated instead, remains attributable in person history, and template edits do not silently rewrite historical completion.

- **CAP-4 — Complete responsible administration**
  - **intent:** An operator can add, edit, remove, and reuse responsibles across tracks with an unambiguous report-recipient effect.
  - **success:** Case variants of the same email cannot duplicate a responsible within one track, cross-track reuse succeeds, and the updated recipient appears in track detail, saved report metadata, and notification projections.

- **CAP-5 — Independent report, notification, and simulated approval projections**
  - **intent:** An operator can understand what was saved, queued, delivered, or still pending without mistaking simulated approval for granted access.
  - **success:** Person/report views independently show durable report save status and path, recipient, notification queued/pending/delivered status with timestamp or error, and only `not_required`, `approval_required`, or `pending_simulated` approval states.

- **CAP-6 — Discoverable operator navigation and catalog flows**
  - **intent:** An operator can reach every required surface and complete supported catalog CRUD without undocumented URLs or raw data editing.
  - **success:** Persistent navigation exposes Dashboard, Review, Onboard, Roles, Tracks, and AI Knowledge; Track detail exposes Tasks and Responsibles; protected role/track deletion returns a clear dependency reason.

- **CAP-7 — Accessible and responsive interaction**
  - **intent:** Keyboard, zoom, assistive-technology, and narrow-screen users can understand and complete the supported UI workflows.
  - **success:** Dialogs, forms, tables, status, focus, validation, htmx feedback, destructive confirmations, and mobile/table behavior meet the acceptance checklist in the UX and gap companions at desktop, 200% zoom, and below 768px.

- **CAP-8 — Regression and end-to-end confidence**
  - **intent:** The implementation can demonstrate every required lifecycle, audit, catalog, projection, accessibility, and responsive behavior through automated and focused acceptance coverage.
  - **success:** `pytest` is available as a required development-environment prerequisite; tests cover the new seams and existing flows; the acceptance run exercises each UI-FR at least once; results are reported from an actual run and never inferred from this unexecuted worktree.

## Constraints

- SQLite remains the local source of truth; schema/query details stay behind `bench/db.py` and `bench/tools`.
- Web routes and templates are thin projections. Shared behavior belongs in `bench/tools` so API, Teams, CLI, and scheduled flows cannot diverge.
- The local actor is `BENCH_ACTOR`, with visible `local-operator` fallback; tests may override it and anonymous audit records are not acceptable.
- People removal is archive-only in the UI. Reports, tasks, notifications, and audit history must survive archive.
- Approval states are exactly `not_required`, `approval_required`, and `pending_simulated`; the local UI never provisions or claims sensitive access was granted.
- Responsible uniqueness is case-insensitive `(track_id, email)`; one responsible may serve multiple tracks.
- Physical task deletion is allowed only before person instantiation. Instantiated tasks are archived/inactivated and retain historical identity.
- Full-page creates and person mutations use POST → 303 → canonical page; inline catalog mutations return only stable targeted fragments, with server confirmation as truth.
- Native semantic HTML, labelled controls/dialogs, keyboard-complete flows, visible focus, text-plus-color status, announced dynamic feedback, 200% readability, and horizontal scrolling for dense narrow tables are acceptance invariants.
- `pytest` must be installed and executable in the development environment before implementation validation or story completion; a missing runner is an environment defect, not a passed or waived test result.
- `python -m pytest --version` and `python -m pytest` are the canonical environment and validation checks.
- A stable `person_id` is the durable identity; email is editable, normalized, and independently validated.
- Successful state-changing mutations and their success audit records commit atomically; rejected attempts may be audited separately without masking the original error.
- A task is permanently instantiated once any historical `person_tasks` row references it; archived instances remain visible in person history and reports.
- Reports remain file-backed for the MVP; SQLite stores report metadata, recipient snapshots, status, path, and timestamps, and a missing file is an explicit unavailable/error state.
- A report snapshots recipients at generation; later responsible changes affect future reports unless an explicit resend is introduced.
- Notification records distinguish queued, pending, delivered, and failed states, with retry/idempotency behavior and delivery outcomes auditable.
- Archived people remain dependencies for role and track deletion; local audit and history records have no automatic retention deletion in this MVP.
- Schema changes are versioned migrations with explicit backfills and fail-closed conflict handling.
- This is a trusted localhost operator tool with simulated permissions and local report/notification records, not a hosted employee-facing system.

## Non-goals

- Hosted authentication, authorization, employee information filtering, or multi-tenancy.
- Real IAM, repository, LMS, Teams delivery guarantees, or other provisioning.
- AWS deployment, AgentCore hosting, EventBridge production scheduling, managed secrets, production observability, or a DynamoDB implementation/migration.
- Bedrock Knowledge Base/RAG, repo-feedback automation, production retention/deletion policy, or permission-template governance.
- Implementing code, modifying existing requirements/UX/architecture/ADR/source/test documents, committing, pushing, or claiming final acceptance in this review proposal.

## Success signal

An operator can discover, perform, and review the complete local Bench lifecycle from the UI: create/edit/archive/restore a person; safely maintain catalog records and responsibles; update progress; generate a durable report; distinguish report save from notification queue/delivery; inspect actor-backed audit history and simulated approvals; and complete the same flows accessibly at supported responsive widths. The result is accepted only after the foundation sequence and explicit approval checklist pass, with test execution evidence from the implementation worktree.

## Assumptions

- An append-only SQLite audit table is sufficient for this local completion slice; external observability remains deferred.
- The existing FastAPI/htmx interaction model and current visual language remain the implementation substrate.
- The requested architecture review is the ratified source for the five accepted decisions supplied by the user.

## Open Questions

- Which exact audit context fields beyond actor, timestamp, entity, action, outcome, and target context are needed for operational debugging?
- What notification delivery adapter/status vocabulary will be used when the future Teams channel becomes hosted, without changing the local projection contract?
