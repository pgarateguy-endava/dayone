---
name: Bench Assistant Local UI
status: final
sources:
  - ../PRODUCT_SPEC.md
  - ../BACKOFFICE_SPEC.md
  - ../ROADMAP.md
  - ../ARCHITECTURE.md
  - ../BENCH_SPEC.md
  - ../../bench/webapp.py
  - ../../tests/test_webapp.py
updated: 2026-07-20
---

# Bench Assistant Local UI — Experience Spine

> This spine owns information architecture, behavior, states, interactions, accessibility, and
> journeys. `DESIGN.md` owns visual identity. When another artifact conflicts with either spine, the
> spines win for this UI completion slice.

## Foundation

Responsive web UI, desktop-first, served locally by the existing FastAPI application and enhanced
with htmx for inline row updates. The primary operator is a manager, People Lead, Resourcing user, or
enablement operator working at a laptop. The Bench engineer uses the same local surface for task
updates and AM/PM check-ins.

This is a trusted localhost MVP. It uses SQLite-backed catalog and state, simulated permissions, and
local report/notification records. It is not a hosted employee-facing product; authentication,
authorization, and per-employee information filtering are prerequisites for that later surface.

Visual references use `DESIGN.md` tokens such as `{colors.ink}`, `{colors.accent}`, `{components.card}`,
and `{rounded.sm}`. The current interaction system remains native HTML forms, tables, dialogs, and
htmx fragment swaps; no new component framework is introduced for completion.

## Information Architecture

| Surface | Reached from | Purpose |
|---|---|---|
| Dashboard | App open / `Dashboard` | Scan people, lifecycle status, progress, blockers, deadline risk, check-ins, activation date, and notification log. |
| Review | Top navigation / employee link | Inspect one employee's progress tree, evidence, blockers, deadline risk, and route to the editable board. |
| Onboard | Top navigation / empty dashboard CTA | Create a person assignment with role/profile, track, start date, and optional PDF. |
| Person detail | Dashboard, Review, post-onboard redirect | Update tasks, complete AM/PM check-ins, view plan, generate EOD report, and inspect lifecycle/access state and action history. |
| Roles | Top navigation / Catalog group | Maintain role/profile summaries, permission boundaries, and approval-required actions. |
| Tracks | Top navigation / Catalog group | Maintain track metadata and open a track detail. |
| Track detail | Track list row | Maintain eligible roles, tasks, and responsibles; show report-recipient effect. |
| AI Knowledge | Top navigation / Catalog group | Maintain mandatory courses, certifications, and suggested-course source records. |

Navigation must expose every catalog surface. `Tracks` must not remain reachable only through an
undocumented URL; task and responsible administration are reached from Track detail and should be
described there as actions, not hidden implementation endpoints.

The information hierarchy is:

1. **Operate people:** Dashboard → Review/Person detail → report and action history.
2. **Define the catalog:** Roles, Tracks → Track detail → Tasks and Responsibles, AI Knowledge.
3. **Start work:** Onboard → Person detail.

## Voice and Tone

Microcopy is short, factual, and action-oriented. The product should help the operator understand
what happened and what to do next.

| Do | Don't |
|---|---|
| `Create bench plan` | `Submit` |
| `Set start date` | `Activate` when the date only triggers local rules |
| `No one is on bench yet. Onboard someone.` | `No data` |
| `Track is assigned to 1 person and cannot be deleted.` | `Delete failed.` |
| `Pending approval — access has not been granted.` | `Access requested successfully.` |
| `Report saved locally. Notification pending.` | `Sent!` when delivery is only queued |
| `Archive Ada Lovelace? Reports and history will be kept.` | `Are you sure?` |

Do not imply real provisioning, approval, or notification delivery when the local MVP only simulates
or queues it. Errors explain the recovery step and stay beside the affected form or row.

## Component Patterns

Behavioral rules; visual treatment lives in `DESIGN.md`.

| Component | Use | Behavioral rules |
|---|---|---|
| Top navigation | All surfaces | Shows current section; catalog links are discoverable; keyboard focus is visible. |
| Summary metric | Dashboard/Review | Shows value plus plain-language label; never communicates risk by color alone. |
| Data table | Catalog and dashboard | Header names the field; actions are in the last column; horizontal scroll is allowed on small screens. |
| Add dialog | Create role/track/task/responsible/knowledge/person | Opens from the relevant card; one form; required fields marked; successful create returns to the relevant detail/list surface. |
| Inline edit row | Role/task/knowledge/responsible | Edit replaces only the row; focus moves to the first editable field; Save returns the row to read mode; Cancel restores original values. |
| Track detail | Track metadata, tasks, responsibles | Saves metadata independently; task and responsible additions do not discard unrelated edits. |
| Confirmation | Delete/archive | Names the record, explains retention or cascade effect, and offers Cancel as the safe default. |
| Status badge | Lifecycle, task, risk, approval | Always paired with text; status changes update the affected row/card after the server confirms. |
| Toast/inline feedback | Mutation result | Success is brief and specific; failure persists until understood or dismissed; form input is retained on failure. |
| Markdown report/plan | Person detail/report | Rendered content is read-only; source record and recipient/delivery status appear outside the rendered markdown. |

## State Patterns

| State | Surface | Behavior and copy |
|---|---|---|
| Loading | Any server-backed mutation | Keep the initiating control associated with the response; do not allow duplicate submits. |
| Empty dashboard | Dashboard | `No one is on bench yet.` Primary action: `Onboard someone`. |
| Empty catalog | Roles/Tracks/Knowledge | Explain the entity's role and offer the create action. |
| Pre-bench | Dashboard/Person | Show `pre_bench`, the date, and the next lifecycle message expected; do not show it as active access. |
| Active | Dashboard/Person | Show progress, today's check-in state, deadline risk, and next action. |
| In-progress edit | Table row | Preserve context; use warm edit background and Save/Cancel. |
| Protected deletion | Role/Track | Keep the record visible and show why deletion is blocked plus the dependent count. |
| Archived person | Dashboard/search/detail | Remove from active dashboard by default; preserve report and action history; provide an explicit archived state. |
| Blocked task/person | Person/Review | Show blocker text, affected task, and responsible follow-up; do not hide the rest of the plan. |
| Pending approval | Person detail | Show requested action and `Pending approval — access has not been granted.` No grant control in this local slice. |
| Report saved / notification pending | Person report/dashboard | Show durable file status separately from delivery queue status. |
| Mutation error | Any form/row | Keep entered values, identify the failed entity, and state the next corrective action. |
| Bench date changed | Dashboard | Confirm the saved date and that lifecycle notifications were re-evaluated immediately. |

## Interaction Primitives

- Use native links for navigation and native forms for committed mutations.
- Use htmx fragment replacement for inline edit/save/delete where the existing row has a stable target.
- Use `303` redirects after full-page creates or person updates so refresh does not repeat a mutation.
- Use one dialog level at a time. Escape closes a dialog; Cancel does not mutate data.
- Enter submits the active form when validation passes. Tab order follows the visual reading order.
- Destructive actions require confirmation. The confirmation names the entity and explains retained or
  deleted data.
- Mutation feedback is attached to the changed row/card, not only shown at the top of the page.
- Do not auto-save catalog fields. Save is an explicit operator action.
- Keep table actions visible on touch-sized viewports; no hover-only affordance.
- For dates, use the browser date control and display the saved ISO date in the record summary.
- Render plan/report markdown as a read-only projection. Never permit it to mutate task, permission,
  or approval state.

## Accessibility Floor

Behavioral requirements; visual contrast and focus colors live in `DESIGN.md`.

- Every input has a visible label; helper text explains the effect of a start date, approval flag, or
  destructive action.
- Every table has a header row and every row action has an accessible name that includes the entity
  where needed, such as `Delete role senior-dev`.
- Dialogs have a programmatic name, move focus to their title or first field, trap focus while open,
  and return focus to the opener when closed.
- Status is conveyed by text plus color; risk and approval states are understandable without color.
- Focus indicators remain visible on links, buttons, inputs, native dialog controls, and htmx-updated
  fragments.
- Validation errors are associated with the relevant field and summarized in plain language.
- Dynamic htmx updates announce meaningful success/error feedback without moving focus unexpectedly.
- Tables remain readable at 200% zoom; horizontal scrolling is acceptable for dense catalog data but
  the row action must remain reachable.
- Respect reduced-motion preferences; no required transition communicates state.
- Keyboard users can complete create, inline edit, cancel, delete confirmation, and check-in flows
  without a pointer.

## Responsive & Platform

| Viewport | Behavior |
|---|---|
| `>= 1024px` | Full top navigation; dashboard metrics in a row; tables use available width. |
| `768–1023px` | Navigation wraps cleanly; summary metrics use two columns; forms remain single-column. |
| `< 768px` | Navigation remains accessible through a labelled menu or wrapped links; cards stack; tables scroll horizontally; person detail prioritizes status, next action, and task updates before the full plan. |

The primary workflow is laptop/desktop. Mobile is a supported read and simple-edit fallback, not a
separate mobile information architecture.

## Safety and Data Boundaries

- Profile permissions and approval-required actions come from role/profile records, never from AI
  knowledge suggestions or rendered markdown.
- The UI displays simulated approval state but never presents request submission as granted access.
- Archived people retain reports and audit history. Catalog deletion is blocked when dependencies make
  removal unsafe.
- Every mutation has an actor, timestamp, entity, action, and outcome in the action log. Until hosted
  identity exists, the local operator identity must be explicit and consistent rather than silently
  absent.
- The localhost trust boundary is visible in the runbook and deployment posture; this UI must not be
  exposed as a shared employee-facing service.

## UI completion amendments

- The visible operator context shows the resolved `BENCH_ACTOR`; `local-operator` is the fallback.
- Person identity is stable by `person_id`; email is editable without rewriting task, report, notification, conversation, or audit history.
- Archived people remain visible through an explicit archived surface and continue to block role/track deletion while historical references exist.
- Archived task instances remain visible in person history and reports with an explicit archived label.
- Reports remain file-backed for this MVP, with saved metadata and recipient snapshots shown outside read-only Markdown.
- Notification projections distinguish queued, pending, delivered, and failed outcomes; simulated approval uses only `not_required`, `approval_required`, and `pending_simulated`.

## Key Flows

### Flow 1 — Start a bench assignment (Laura, People Lead, Monday morning)

1. Laura opens Dashboard and sees that no one is active for the new cohort.
2. She chooses `Onboard someone`.
3. She enters the employee name and email, selects the role/profile and track, sets the bench start
   date, and optionally uploads the profile PDF.
4. She submits `Create bench plan`.
5. The system validates the role and track, creates the state and tasks, evaluates the date-triggered
   lifecycle, and redirects to Person detail.
6. The detail view shows the plan, task progress, risk state, approval flags, and report action.
7. **Climax:** Laura can see the exact next step and the truth boundary—what is requested or pending,
   what is simulated, and what has not been granted—without opening another system.

Failure: invalid role/track or duplicate email keeps Laura's entered values and states the correction
beside the field; no partial onboarding record is presented as successful.

### Flow 2 — Maintain a track and its recipients (Diego, enablement operator, before a cohort)

1. Diego opens Tracks from the visible navigation and selects the target track.
2. He edits the duration or eligible roles and saves track settings.
3. He adds or edits a task with deadline, cadence, evidence, approval, and reference contact.
4. He adds a responsible, edits the notification role, and sees the recipient in the track detail.
5. He generates a test EOD report for a person assigned to the track.
6. **Climax:** the report and notification log show the same responsible recipient Diego just configured.

Failure: attempting to delete an assigned track leaves it visible and names the dependent people; no
cascade occurs silently.

### Flow 3 — Complete the daily cycle (Sofía, Bench engineer, end of day)

1. Sofía opens her Person detail from the link provided by the operator.
2. She reviews the task list and updates a task status with evidence.
3. She completes the PM check-in and records any blocker.
4. The system verifies progress deterministically and generates the EOD report.
5. She opens the report and sees its recipients, durable local record, and notification queue status.
6. **Climax:** Sofía leaves with an accurate record of what she completed and what remains blocked; the
   report gives the responsible people the same facts without requiring a separate status message.

Failure: an update fails, the evidence remains in the form and the UI explains how to retry; generated
plan/report prose never changes the stored task status.

### Flow 4 — Review a sensitive request (Marcos, approver, local MVP boundary)

1. Marcos opens Review and selects an employee.
2. He sees the requested permission and its `Pending approval` state in the employee detail.
3. The UI explains that submission is not a grant and provides no real provisioning control in this
   local slice.
4. **Climax:** Marcos can distinguish an auditable request from a granted permission and knows the
   approval execution is outside the local MVP.
