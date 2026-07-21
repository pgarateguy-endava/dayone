---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - docs/spec-review-dayone-bench-ui/SPEC.md
  - docs/spec-review-dayone-bench-ui/change-summary.md
  - docs/spec-review-dayone-bench-ui/current-state-gap-matrix.md
  - docs/spec-review-dayone-bench-ui/traceability.md
  - docs/spec-review-dayone-bench-ui/epic-story-implications.md
  - docs/spec-review-dayone-bench-ui/approval-checklist.md
  - docs/spec-review-dayone-bench-ui/items-must-not-change.md
  - docs/ux-dayone-bench/DESIGN.md
  - docs/ux-dayone-bench/EXPERIENCE.md
  - docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md
  - docs/adr/0001-bench-as-parallel-domain.md
  - docs/adr/0002-hybrid-strands-langgraph.md
  - docs/adr/0003-relational-catalog-sqlite.md
  - docs/adr/0004-teams-bot-thin-channel.md
  - docs/PRODUCT_SPEC.md
  - docs/BACKOFFICE_SPEC.md
  - docs/ROADMAP.md
  - docs/BENCH_SPEC.md
  - docs/ARCHITECTURE.md
---

# DayOne Bench UI - Epic Breakdown

## Overview

This planning artifact decomposes the approved `SPEC-dayone-bench-ui` target contract into implementation epics and stories. The SPEC is canonical; architecture, ADR, UX, and source requirements are supporting context. The six epics follow the ratified foundation sequence and are implementation planning only.

## Requirements Inventory

### Functional Requirements

UI-FR-001: The operator can reach Dashboard, Review, Onboard, Roles, Tracks, Tasks, Responsibles, and AI Knowledge from discoverable web UI navigation.

UI-FR-002: The operator can create a bench onboarding record with name, email, role/profile, track, optional start date, and optional profile PDF, with validation and redirect to the created record.

UI-FR-003: Employee detail and review expose derived lifecycle (`inactive`, `pre_bench`, `active`), date, profile, track, progress, blockers, deadline risk, check-ins, plan, and report.

UI-FR-004: The operator can edit person fields and archive/remove a person with confirmation; durable reports and action history are preserved.

UI-FR-005: The operator can create, inline-edit, and delete roles/profiles; deletion is blocked with an actionable reason while assigned to an active employee.

UI-FR-006: The operator can create, edit, and delete tracks, including duration and eligible roles; deletion is blocked while assigned to an active employee.

UI-FR-007: The operator can add, inline-edit, and delete task templates with their catalog fields; changes explicitly affect future assignments and do not rewrite existing history without confirmation.

UI-FR-008: The operator can create, inline-edit, and delete knowledge records for mandatory courses, certifications, and suggested courses.

UI-FR-009: The operator can add, edit, and remove track responsibles and notification roles; track detail shows recipients and report-delivery effect.

UI-FR-010: An operator or employee can update task status/evidence, complete AM/PM check-ins, and see deterministic verification; generated text never overrides stored state.

UI-FR-011: The UI can generate an EOD report, show recipient snapshots, preserve a durable local report record, expose notification pending/delivered status, and immediately re-evaluate lifecycle notifications after a date change.

UI-FR-012: Employee and operator views show simulated approval state without claiming access was granted or performing real provisioning.

UI-FR-013: Every create, edit, archive/delete, status/date/approval change, report generation, and notification-delivery action records actor, time, entity, action, outcome, and exposes the action log on employee detail.

### NonFunctional Requirements

UI-NFR-001: Run locally with SQLite and simulated permissions; preserve compatibility with the API/storage seam for a future DynamoDB path.

UI-NFR-002: Keep permission data profile-owned, escape user values, require destructive confirmation, and return actionable validation errors.

UI-NFR-003: Automated coverage includes happy paths, validation, protected deletion, inline edit, lifecycle, responsibles, reports, and date changes; acceptance executes every UI-FR.

UI-NFR-004: Keep the localhost trust boundary explicit; hosted authentication, authorization, and employee filtering are outside this slice.

### Additional Requirements

- SQLite is authoritative for Bench catalog/state; rendered Markdown and UI state are projections.
- Shared behavior belongs in `bench/tools`; web, API, Teams, CLI, and scheduled paths must use the same seams.
- Use `BENCH_ACTOR`, with visible `local-operator` fallback; tests may override it and anonymous audit records are not acceptable.
- Successful mutation and success audit commit atomically where possible; failed attempts may be audited without masking the original error.
- Introduce stable `person_id`; email is normalized/editable and must not rewrite task, check-in, report, notification, conversation, or audit history.
- People removal is archive-only in the UI; archived people remain restorable and preserve all history and dependencies.
- A task is physically deletable only before person instantiation; instantiated tasks are archived/inactivated and remain attributable in history and reports.
- Responsible uniqueness is case-insensitive `(track_id, email)`; cross-track reuse is allowed.
- Reports remain file-backed for MVP, with SQLite metadata, recipient snapshot, status, path, timestamps, and explicit unavailable/error state when files are missing.
- Report save and notification queue/pending/delivered/failed projections are independent; approval vocabulary is exactly `not_required`, `approval_required`, `pending_simulated`.
- Full-page creates/person mutations use POST → 303 → canonical page; inline mutations return stable targeted fragments with server confirmation as truth.
- Versioned migrations require explicit backfills, fail-closed conflict handling, no automatic local history deletion, and documented backup/reset procedures.
- Persistent navigation exposes Dashboard, Review, Onboard, Roles, Tracks, and AI Knowledge; Tasks and Responsibles are reached from Track detail.
- Native semantic HTML, labels, dialog semantics, keyboard completion, visible focus, text-plus-color statuses, announced htmx feedback, 200% readability, and responsive narrow-table/navigation behavior are acceptance invariants.
- `python -m pytest --version` and `python -m pytest` are required environment/validation commands; missing pytest is an environment defect, not a waived result.
- Keep Bench isolated as a parallel domain; preserve Strands conversation, LangGraph daily-cycle, deterministic writes, and thin Teams channel boundaries.

### UX Design Requirements

UX-DR1: Preserve the existing dark navigation, warm paper canvas, white cards, orange creation accent, system sans typography, spacing scale, and semantic status color pairs.
UX-DR2: Provide persistent discoverable navigation with perceivable active state; at narrow widths use a labelled menu or cleanly wrapped links.
UX-DR3: Use native semantic forms, tables, links, buttons, and one-form dialogs; expose visible labels, helper text, named destructive confirmations, and verb-led actions.
UX-DR4: Implement stable inline edit fragments with focus to first field, adjacent Save/Cancel, read-mode restoration, retained failed input, and associated error feedback.
UX-DR5: Make status understandable through text plus color for lifecycle, task, risk, approval, report, and notification states; never imply provisioning or delivery from simulation/queue.
UX-DR6: Implement dialog focus naming, focus movement/trap/return, Escape/Cancel safety, visible focus, keyboard-complete flows, and reduced-motion support.
UX-DR7: Announce meaningful htmx success/error updates without unexpected focus movement; keep feedback beside the changed row/card.
UX-DR8: At 200% zoom preserve readable tables and reachable row actions; below 768px stack cards, keep navigation accessible, horizontally scroll dense tables, and prioritize person status/task actions.
UX-DR9: Keep read-only plan/report Markdown separate from durable source records, recipient metadata, delivery state, and approval state.

### FR Coverage Map

UI-FR-001: Epic 4 - Discoverable navigation and catalog administration
UI-FR-002: Epic 2 - People lifecycle and history safety
UI-FR-003: Epic 2 - People lifecycle and history safety
UI-FR-004: Epic 2 - People lifecycle and history safety
UI-FR-005: Epic 4 - Discoverable navigation and catalog administration
UI-FR-006: Epic 4 - Discoverable navigation and catalog administration
UI-FR-007: Epic 2 and Epic 4 - history-safe task behavior and task-template CRUD
UI-FR-008: Epic 4 - Discoverable navigation and catalog administration
UI-FR-009: Epic 3 - Responsibles and status projections
UI-FR-010: Epic 2 and Epic 6 - safe progress behavior and automated verification
UI-FR-011: Epic 3 - durable report and notification projections
UI-FR-012: Epic 3 - simulated approval projection
UI-FR-013: Epic 1 and Epic 3 - shared mutation audit and projected action history

UI-NFR-001: Epic 1 - SQLite authority and channel/tool storage seam
UI-NFR-002: Epics 1, 2, 3, 4, and 5 - safety, escaping, confirmation, and actionable errors
UI-NFR-003: Epic 6 - complete automated and acceptance coverage
UI-NFR-004: Epic 6 - explicit localhost trust-boundary regression

## Epic List

### Epic 1: Durable foundation and mutation audit

Operators and every Bench channel can rely on durable SQLite-backed facts, stable identity, explicit actor context, and auditable shared mutations.
**FRs covered:** UI-FR-013; UI-NFR-001–002

### Epic 2: People lifecycle and history safety

Operators can onboard, edit, archive, restore, and update people while preserving identity, task history, reports, notifications, and lifecycle semantics.
**FRs covered:** UI-FR-002–004, UI-FR-007, UI-FR-010

### Epic 3: Responsibles and status projections

Operators can maintain recipients and understand independent report-save, notification, and simulated-approval states without confusing projections for delivery or access.
**FRs covered:** UI-FR-009, UI-FR-011–013

### Epic 4: Discoverable navigation and catalog administration

Operators can discover and safely maintain roles, tracks, tasks, knowledge, and track responsibles through documented catalog flows.
**FRs covered:** UI-FR-001, UI-FR-005–009

### Epic 5: Accessible responsive operator workflows

Operators can complete supported people and catalog workflows with semantic, keyboard-complete, understandable, and responsive UI behavior.
**FRs covered:** UI-FR-001–013; UI-NFR-002

### Epic 6: Verification and acceptance confidence

The team can prove the complete contract through executable pytest checks, migrations, cross-channel consistency, UI-FR traceability, accessibility, responsive, and regression acceptance.
**FRs covered:** UI-FR-001–013; UI-NFR-003–004

<!-- Stories are added after epic-list approval. -->

## Epic 1: Durable foundation and mutation audit

This epic establishes the shared, durable foundation required by every later user-facing workflow. SQLite remains authoritative, storage details remain behind tools, and no channel owns business rules.

### Story 1.1: Version the Bench schema and backfill durable identity and lifecycle fields

As a Bench operator,
I want existing Bench databases upgraded through explicit versioned migrations,
So that new lifecycle, stable identity, and history fields are available without silently losing data.

**Acceptance Criteria:**

**Given** an existing database at each supported pre-migration schema version
**When** the application runs the migration path
**Then** migrations are applied in version order and are idempotent
**And** this story creates only the stable `person_id`, normalized email support, lifecycle/archive fields, and task active/archive fields needed by the people and task-history stories.

**Given** duplicate person identities or case-insensitive responsible conflicts are encountered during backfill
**When** the migration validates the data
**Then** it fails closed with an actionable conflict and does not invent or merge identity silently
**And** no automatic local task, report, notification, check-in, conversation, or audit history deletion occurs.

**Given** a person whose email is later edited
**When** historical rows are queried by stable identity
**Then** all historical references remain attached to the same `person_id`.

**Test implications:** Migration tests cover old schemas, repeated upgrades, backfill success, conflict failure, stable identity, and preservation of every historical table.

**Implementation boundary:** Audit storage is introduced with Story 1.3; report metadata with Story 3.2; notification projection fields with Story 3.3.

### Story 1.2: Resolve and propagate the explicit local actor

As an operator,
I want the resolved Bench actor visible and consistent across channels,
So that every mutation has an accountable local identity.

**Acceptance Criteria:**

**Given** `BENCH_ACTOR` is set
**When** a web, API, Teams, CLI, or scheduled mutation runs
**Then** the shared tool context records that value as the actor
**And** the channel does not substitute a channel-local actor.

**Given** `BENCH_ACTOR` is unset or blank
**When** the local UI context is rendered
**Then** the visible actor is `local-operator`
**And** no mutation produces an anonymous audit actor.

**Given** a test overrides the actor
**When** the mutation completes
**Then** the override is observable in the audit record and does not leak into unrelated test cases.

**Test implications:** Unit tests cover resolution and fallback; API, web, CLI, Teams-adapter, and scheduled-call contract tests assert identical actor propagation.

### Story 1.3: Audit shared mutations atomically and expose action history queries

As an operator,
I want mutation outcomes recorded with actor and target context,
So that lifecycle and catalog changes can be explained after the fact.

**Acceptance Criteria:**

**Given** a supported create, edit, archive/delete, status/date, approval-display, report, or notification mutation succeeds
**When** the transaction commits
**Then** one append-only audit record stores actor, timestamp, entity type/id, action, outcome, and target/detail context in the same transaction where possible
**And** the returned projection reflects the committed SQLite state.

**Given** a mutation is rejected
**When** an error is returned
**Then** the original actionable error remains intact
**And** a rejected outcome is recorded only if it can be persisted without masking that error.

**Given** an employee detail is opened
**When** action history is requested
**Then** records are ordered deterministically and scoped to the stable person identity where applicable.

**Test implications:** Transaction tests cover success rollback coupling, rejected mutations, append-only behavior, required fields, ordering, and person-scoped history.

### Story 1.4: Establish channel-consistent domain tool contracts

As a developer maintaining Bench,
I want shared domain-shaped tool operations for reads and mutations,
So that UI, API, Teams, CLI, and scheduled flows cannot diverge.

**Acceptance Criteria:**

**Given** a behavior is required by more than one channel
**When** it is implemented
**Then** business rules and SQLite access live behind `bench/tools` and storage seams
**And** web routes/templates contain projection and HTTP composition only.

**Given** a UI mutation is successful
**When** the response is selected
**Then** full-page creates/person mutations use POST → 303 → canonical page
**And** inline mutations return only the stable targeted fragment after server confirmation.

**Given** a later storage adapter is substituted
**When** a tool operation is called
**Then** its domain-shaped contract remains unchanged and no template/route depends on SQLite-specific details.

**Test implications:** Contract tests exercise the same operation through web/API and representative CLI/Teams/scheduled entry points, asserting equal persisted facts and response semantics.

## Epic 2: People lifecycle and history safety

### Story 2.1: Create and edit people with stable identity and validation

As a People Lead,
I want to create and edit a person's assignment details,
So that onboarding records remain accurate without changing historical identity.

**Acceptance Criteria:**

**Given** valid name, normalized email, role/profile, track, optional start date, and optional profile context
**When** the operator submits onboarding
**Then** the person and instantiated task rows are committed in SQLite, lifecycle is evaluated, and the response redirects 303 to person detail.

**Given** an invalid role/track, duplicate identity, malformed email, or invalid profile input
**When** the form is submitted
**Then** no partial onboarding record is presented as successful, entered values are retained, and the field-level error explains correction.

**Given** an existing person is edited, including email
**When** the save succeeds
**Then** the same `person_id` remains authoritative and historical tasks, check-ins, reports, notifications, conversations, and audit rows remain attached.

**Test implications:** API/UI tests cover valid creation, each validation failure, duplicate handling, 303 behavior, email normalization, and complete historical-reference preservation.

### Story 2.2: Archive, list, restore, and inspect people safely

As an operator,
I want archive and restore actions with explicit active/archived views,
So that removal is reversible and never destroys history.

**Acceptance Criteria:**

**Given** an active person
**When** the operator confirms archive
**Then** only archive state changes, the person leaves active dashboard/review queries, and the UI names the retained reports, tasks, notifications, and audit history.

**Given** an archive confirmation is cancelled
**When** the dialog closes
**Then** no data or audit mutation occurs.

**Given** an archived person is viewed
**When** the archived surface is opened
**Then** the person, plan, task history, reports, notifications, and action history remain readable with an archived label and a restore action.

**Given** restore is confirmed
**When** it succeeds
**Then** the person returns to active queries according to derived date status and the audit record identifies archive/restore actor and outcome.

**Test implications:** Lifecycle tests cover active/archived filtering, confirmation cancellation, restore, dependency retention, and no-cascade guarantees.

### Story 2.3: Preserve instantiated task history through catalog changes

As an operator,
I want task templates to respect person-task history,
So that catalog maintenance cannot erase completed or blocked work.

**Acceptance Criteria:**

**Given** a task template has no `person_tasks` references
**When** the operator confirms deletion
**Then** physical deletion is allowed and the action is audited.

**Given** a task template has any historical person instance
**When** the operator requests deletion or inactivation
**Then** the template is archived/inactivated instead of physically deleted
**And** every instantiated task remains attributable, visible in person history/reports, and explicitly labelled archived where applicable.

**Given** a task template is edited
**When** the edit is saved
**Then** future assignment behavior is explicit and existing person-task status, evidence, notes, timestamps, and identity are not silently rewritten.

**Test implications:** Instantiate-before-delete tests cover physical-delete eligibility, archived visibility, historical identity, edits, reports, and regression against destructive reset behavior.

### Story 2.4: Re-evaluate lifecycle immediately after date changes

As an operator,
I want saved bench-date changes to re-evaluate lifecycle notifications immediately,
So that the displayed state and pending work match the new date.

**Acceptance Criteria:**

**Given** a person has a valid new bench start date
**When** the operator saves it
**Then** the date is committed, derived state is recalculated immediately, relevant lifecycle notifications are evaluated, and the canonical person page confirms the saved ISO date.

**Given** the date is invalid or the save fails
**When** submission returns
**Then** the original date remains unchanged, entered input and an actionable error remain visible, and no false notification status is shown.

**Given** a date change succeeds
**When** action history is inspected
**Then** the actor, date action, outcome, and lifecycle evaluation context are present.

**Test implications:** UI/API tests cover pre-bench/active/inactive transitions, notification re-evaluation, invalid dates, atomic failure, redirect behavior, and audit context.

## Epic 3: Responsibles and status projections

### Story 3.1: Maintain responsible assignments with safe uniqueness

As an enablement operator,
I want to add, edit, remove, and reuse responsibles across tracks,
So that report recipients stay correct without duplicate or destructive assignments.

**Acceptance Criteria:**

**Given** a responsible email is new for a track
**When** it is added or edited
**Then** the normalized responsible and notification role appear in track detail and the mutation is audited.

**Given** the same email differs only by case within one track
**When** it is added or edited
**Then** the operation is rejected with an actionable uniqueness error and no duplicate is created.

**Given** the email already serves another track
**When** it is assigned to the current track
**Then** cross-track reuse succeeds and each track retains its own assignment/role effect.

**Given** a responsible is removed
**When** confirmation is accepted
**Then** the assignment is removed without deleting report history or rewriting prior recipient snapshots.

**Test implications:** Unit/API/UI tests cover case variants, cross-track reuse, edit/remove, confirmation cancellation, recipient projection, and audit outcomes.

### Story 3.2: Persist and project durable report records

As an operator,
I want report generation to produce a durable record separate from rendered Markdown,
So that I can tell what was saved and who was included.

**Acceptance Criteria:**

**Given** deterministic progress data and a recipient list
**When** an EOD report is generated
**Then** the file-backed report and SQLite metadata record include stable identity, person/date, path, save status, timestamp, and a recipient snapshot.

**Given** the report file is missing or cannot be read
**When** the report is viewed
**Then** the UI shows an explicit unavailable/error state and does not treat metadata as readable content.

**Given** responsibles change after a report is saved
**When** the saved report is inspected
**Then** its recipient snapshot remains unchanged and later reports use the new recipients.

**Test implications:** Report tests cover generation, repeat/idempotence behavior, metadata/path, missing files, recipient snapshots, read-only rendering, and actor audit.

### Story 3.3: Project independent notification lifecycle status

As an operator,
I want queued, pending, delivered, and failed notification state shown independently,
So that a locally saved report is never mistaken for delivery.

**Acceptance Criteria:**

**Given** a report notification is created
**When** the projection is rendered
**Then** recipient, queued/pending state, timestamp where available, and retry/idempotency identity are visible separately from report save status.

**Given** delivery succeeds, remains pending, or fails
**When** the notification record is refreshed
**Then** the UI shows delivered, pending/queued, or failed with delivery timestamp/error as applicable.

**Given** a retry is requested for a failed notification
**When** it is processed
**Then** the outcome is auditable and duplicate delivery is prevented according to the notification idempotency contract.

**Test implications:** Projection tests cover every transition, timestamps/errors, report/notification independence, retry, idempotency, and API/UI consistency.

### Story 3.4: Show simulated approval states without granting access

As a reviewer,
I want approval requirements and simulated state explained clearly,
So that a request is not confused with sensitive access being granted.

**Acceptance Criteria:**

**Given** profile/task facts indicate no approval is needed
**When** person or operator detail is rendered
**Then** the state is exactly `not_required` with non-granting explanatory copy.

**Given** approval is required or locally pending
**When** the projection is rendered
**Then** the state is exactly `approval_required` or `pending_simulated` and copy states that access has not been granted.

**Given** any generated text or submitted request suggests granted access
**When** the UI/API response is built
**Then** it is rejected or normalized to the ratified vocabulary and no IAM/repository provisioning occurs.

**Test implications:** Unit/API/UI assertions cover all three allowed states and reject `granted`, `approved`, or delivery language that implies real provisioning.

## Epic 4: Discoverable navigation and catalog administration

### Story 4.1: Expose persistent navigation and documented catalog entry points

As an operator,
I want every required Bench surface reachable from visible navigation,
So that workflows do not depend on undocumented URLs.

**Acceptance Criteria:**

**Given** any supported Bench page is open
**When** the operator inspects navigation
**Then** Dashboard, Review, Onboard, Roles, Tracks, and AI Knowledge are visible destinations with a perceivable active location.

**Given** a track is selected
**When** Track detail opens
**Then** Tasks and Responsibles are clearly presented as documented child actions.

**Given** a narrow viewport or keyboard navigation
**When** the operator moves through the navigation
**Then** all destinations remain reachable, labelled, focus-visible, and usable without hover.

**Test implications:** Route/link tests cover all destinations and active state; markup/keyboard tests cover focus and narrow navigation behavior.

### Story 4.2: Maintain roles and tracks with dependency-safe deletion

As a catalog operator,
I want to maintain roles and tracks without orphaning assigned people,
So that catalog deletion remains safe and understandable.

**Acceptance Criteria:**

**Given** valid role/profile or track fields
**When** create/edit is saved
**Then** SQLite is updated through shared tools, the relevant list/detail projection confirms the server state, and the action is audited.

**Given** a role or track has active or archived person dependencies
**When** deletion is requested
**Then** deletion is blocked, the record remains visible, and a human-readable message names the dependency and count.

**Given** a deletion is safe and confirmed
**When** it completes
**Then** only the intended catalog record is deleted and unrelated assignments/history remain intact.

**Test implications:** API/UI tests cover CRUD, escaping, protected deletion for active and archived dependencies, confirmation cancellation, and atomic audit behavior.

### Story 4.3: Maintain task templates and knowledge records through safe inline CRUD

As a catalog operator,
I want to maintain tasks and AI knowledge records through focused forms,
So that catalog facts are editable without raw data or accidental history changes.

**Acceptance Criteria:**

**Given** a task or knowledge record form is opened
**When** the operator saves valid fields
**Then** the server validates and persists the record, returns the canonical row/detail projection, and escapes user-provided values.

**Given** an inline edit fails
**When** the fragment returns
**Then** only the stable target is replaced, entered values remain, and the associated corrective error is shown.

**Given** a task deletion is requested
**When** the task-history safety rule is evaluated
**Then** pre-instantiation deletion or post-instantiation archive behavior from Story 2.3 is applied, with explicit effect on future assignments.

**Test implications:** CRUD tests cover all task and knowledge fields, inline fragment targets, validation/escaping, keyboard cancel, and task-history regression.

### Story 4.4: Provide independent Track detail administration

As an enablement operator,
I want track metadata, tasks, eligible roles, and responsibles managed from one detail surface,
So that I can understand catalog and recipient effects together.

**Acceptance Criteria:**

**Given** Track detail is opened
**When** metadata, eligible roles, tasks, or responsibles are changed independently
**Then** each save commits only its intended domain fact and does not discard unrelated edits.

**Given** a task or responsible row is edited inline
**When** save or cancel completes
**Then** the stable row returns to read mode or original values and the response contains no unrelated rows.

**Given** a responsible is configured
**When** the detail projection refreshes
**Then** the complete recipient list and report-delivery effect are explicit.

**Test implications:** Track-detail integration tests cover independent saves, fragment boundaries, recipient effect, protected deletion feedback, and API parity.

## Epic 5: Accessible responsive operator workflows

### Story 5.1: Make forms and dialogs semantic and keyboard complete

As an operator using a keyboard or assistive technology,
I want forms and confirmations to have clear names and predictable focus,
So that I can complete every supported mutation without a pointer.

**Acceptance Criteria:**

**Given** a create/edit/destructive dialog opens
**When** focus enters it
**Then** it has a programmatic name, focus moves to its title or first field, focus remains contained while open, and focus returns to the opener on close.

**Given** a form is rendered
**When** it is inspected or completed by keyboard
**Then** every input has a visible label, required/helper text, associated validation, logical Tab order, and Enter submission where valid.

**Given** Cancel, Escape, or a destructive confirmation is used
**When** the operator declines
**Then** no mutation occurs and the confirmation names the entity and retention/cascade effect.

**Test implications:** Automated markup checks plus keyboard-oriented acceptance cover roles, labels, dialog naming, focus trap/return, Escape, Cancel safety, and validation association.

### Story 5.2: Provide stable, announced mutation feedback

As an operator,
I want mutation success and failure attached to the changed record,
So that htmx enhancements remain understandable and recoverable.

**Acceptance Criteria:**

**Given** an inline mutation succeeds
**When** the server confirms it
**Then** only the stable target fragment updates, the row returns to read mode, and concise success feedback is announced without unexpected focus movement.

**Given** a mutation fails
**When** the response is returned
**Then** the affected form/row retains entered values, the error is associated and persistent until understood/dismissed, and no optimistic state remains.

**Given** a full-page create or person mutation succeeds
**When** the response is followed
**Then** POST → 303 prevents duplicate refresh submission and the canonical page reflects committed state.

**Test implications:** htmx response/markup tests cover stable IDs, swaps, announcements, focus preservation, retained errors, 303 redirects, and server-confirmed state.

### Story 5.3: Make status, tables, and navigation readable at zoom and narrow widths

As an operator on a small screen or at 200% zoom,
I want dense Bench information to remain readable and actionable,
So that responsive support does not hide operational controls.

**Acceptance Criteria:**

**Given** lifecycle, task, risk, approval, report, or notification status is displayed
**When** color is unavailable or ignored
**Then** visible text still communicates the state and no status depends on color alone.

**Given** the viewport is below 768px or zoom is 200%
**When** dashboard/catalog/person detail is opened
**Then** cards stack as appropriate, dense tables scroll horizontally, headers remain meaningful, and row actions remain reachable and named.

**Given** the viewport is 768–1023px or at least 1024px
**When** layout is rendered
**Then** navigation, metrics, forms, and tables follow the agreed breakpoint behavior without changing information order.

**Test implications:** Responsive screenshots/manual acceptance and automated contrast/markup checks cover breakpoints, zoom, table scrolling, action reachability, status text, and active navigation.

## Epic 6: Verification and acceptance confidence

### Story 6.1: Add focused unit and API coverage for durable domain seams

As an implementation team,
I want focused automated coverage for each new domain seam,
So that regressions fail close to the source of truth.

**Acceptance Criteria:**

**Given** the new migration, identity, lifecycle, actor, audit, responsible, task-safety, report, notification, and approval operations exist
**When** the focused suite runs
**Then** each operation has unit/API coverage for success, validation failure, atomicity, and boundary behavior.

**Given** the same operation is invoked through web and API channels
**When** results are compared
**Then** persisted SQLite facts, actor, audit outcome, and projection vocabulary are consistent.

**Given** a legacy shipped flow is exercised
**When** the regression suite runs
**Then** existing onboarding, deterministic progress, check-in, report generation, token/API, and hybrid-engine behavior remains intact.

**Test implications:** This story is the test implementation itself; coverage names and fixtures must identify the contract/decision they protect.

### Story 6.2: Exercise every UI-FR through UI and end-to-end scenarios

As a product owner,
I want an acceptance run that exercises every UI-FR at least once,
So that completion reflects observable operator outcomes rather than isolated implementation tests.

**Acceptance Criteria:**

**Given** a clean local database and supported test environment
**When** the UI/E2E acceptance suite runs
**Then** UI-FR-001 through UI-FR-013 each map to at least one named automated or manual scenario with result evidence.

**Given** protected deletion, duplicate responsible, date change, archive/restore, email edit, missing report file, pending notification, and simulated approval cases
**When** the scenarios run
**Then** each expected safety boundary and user-visible message is asserted.

**Given** generated plan/report content is rendered
**When** the scenario attempts to treat it as mutable state or granted access
**Then** the UI keeps it read-only and preserves the approved trust boundary.

**Test implications:** Maintain the traceability matrix in this artifact and link each scenario to its test/manual evidence; no unexecuted result may be claimed.

### Story 6.3: Validate accessibility and responsive acceptance paths

As an operator with varied access needs,
I want acceptance coverage for keyboard, assistive-technology-oriented markup, zoom, and responsive behavior,
So that accessibility is a release criterion rather than optional polish.

**Acceptance Criteria:**

**Given** create, inline edit, cancel, delete confirmation, check-in, and navigation flows
**When** they are completed with keyboard-only interaction
**Then** every flow is completable with visible focus and no hover-only action.

**Given** the UI is inspected at 200% zoom and below 768px
**When** dense pages and dynamic updates are used
**Then** statuses, validation, announcements, tables, navigation, and row actions remain understandable and reachable.

**Given** reduced motion is requested
**When** state changes occur
**Then** no required state meaning depends on animation.

**Test implications:** Combine automated semantic/ARIA/label checks with documented manual keyboard, screen-reader-oriented, zoom, responsive, and reduced-motion acceptance evidence.

### Story 6.4: Make pytest and migration operations explicit release prerequisites

As a developer,
I want a reproducible test environment and documented local data procedures,
So that missing tooling or unsafe upgrades cannot be mistaken for passing acceptance.

**Acceptance Criteria:**

**Given** a development worktree is prepared
**When** `python -m pytest --version` is run
**Then** an executable pytest runner is available; absence is reported as an environment defect and blocks story completion.

**Given** migrations are applied to representative old databases
**When** the upgrade and rollback/failure paths are exercised
**Then** version history, explicit backfills, fail-closed conflicts, atomic failure behavior, and backup/reset instructions are documented.

**Given** the final suite is reported
**When** `python -m pytest` runs
**Then** results are copied from the actual run, include the environment check, and do not infer success from this planning artifact.

**Test implications:** CI/local setup checks enforce pytest availability; migration fixtures and run logs cover upgrades, backup/reset, indefinite local history, and no automatic deletion.

## UI-FR Traceability Matrix

| UI-FR | Epic/story coverage | Acceptance evidence |
|---|---|---|
| UI-FR-001 | 4.1, 5.3, 6.2 | Navigation/link, active-state, keyboard, responsive, E2E scenario |
| UI-FR-002 | 2.1, 5.1, 5.2, 6.2 | Onboarding validation, 303 redirect, identity, keyboard/UI scenario |
| UI-FR-003 | 2.1, 2.2, 2.4, 3.2–3.4, 6.2 | Lifecycle/detail, progress, report, approval, action projection scenario |
| UI-FR-004 | 2.1–2.2, 5.1–5.2, 6.2 | Edit, archive/restore, confirmation, retained-history scenario |
| UI-FR-005 | 4.2, 5.1–5.2, 6.2 | Role CRUD, protected deletion, inline/keyboard scenario |
| UI-FR-006 | 4.2, 4.4, 5.3, 6.2 | Track CRUD/detail, dependency reason, responsive scenario |
| UI-FR-007 | 2.3, 4.3, 4.4, 6.1–6.2 | Template CRUD, instance archive, history regression |
| UI-FR-008 | 4.3, 5.1–5.2, 6.2 | Knowledge CRUD, validation, escaping, inline scenario |
| UI-FR-009 | 3.1, 4.4, 6.1–6.2 | Responsible uniqueness/reuse, recipient effect, audit |
| UI-FR-010 | 2.4, 6.1–6.2 | Progress/check-in, deterministic state, date evaluation |
| UI-FR-011 | 3.2–3.3, 2.4, 6.1–6.2 | Durable report, recipient snapshot, notification transitions |
| UI-FR-012 | 3.4, 5.3, 6.1–6.2 | Exact approval vocabulary and non-granting copy |
| UI-FR-013 | 1.2–1.3, 3.1–3.4, 6.1–6.2 | Actor-backed audit fields, outcomes, action history |
