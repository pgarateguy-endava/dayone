# Product spec — onboarding assistant

> **This document owns:** what the assistant IS as a product — personas, journeys, scope, data model,
> metrics. **It does not own:** how the workshop teaches it — see [`PEDAGOGY_SPEC.md`](PEDAGOGY_SPEC.md).

## Organizing principle

The deterministic plan generator (`agent/tools/generate_plan.py`) **stays**, but it is demoted from
"the demo" to **one tool the agent calls**. The agent — backed by Knowledge Base RAG, Memory, and a
human-in-the-loop approval gate — is the primary surface. This satisfies all three constraints
(agentic, AWS+Strands, onboarding accelerator) at once: the accelerator keeps its deterministic,
audit-safe core, while the genuinely agentic value (grounded Q&A, continuity, judgment) is what the
user actually talks to.

## Problem statement

Per `WORKSHOP_OBJECTIVES.md`: reduce the time for a new developer to become productive from day 1.
Concretely, that time is lost to three things this product targets directly:
1. Re-asking the same context questions repeatedly (Slack/Confluence archaeology).
2. Waiting on a human to confirm permissions or access status.
3. Losing track of which onboarding steps are already done across multiple days/sessions.

## Personas

**Primary — New-hire developer.** Needs: a concrete first plan, a place to ask "why/how" questions
without waiting on a teammate, confidence the answers are accurate (not guessed), and a record of what
they've already done. Success moment: by end of day 1 they've cloned the right repos, understand the
architecture summary, and know their first task — without scheduling a meeting to get there.

**Secondary — Approver (manager / onboarding buddy).** Needs: visibility into what was requested or
granted, a low-friction way to approve or deny sensitive actions, and confidence the agent will never
silently grant access it isn't authorized to grant.

## Journeys

Each journey states inputs, what the agent does, outputs, the AgentCore primitive backing it, and its
grounding rule (see [Hallucination-tolerance policy](#hallucination-tolerance-policy-per-journey)).

### J1 — Day-1 plan generation
- **Input:** employee name, email, profile id, project id.
- **Agent behavior:** calls `load_profile` + `load_project` + `generate_onboarding_plan` (deterministic tools — already shipped).
- **Output:** Markdown plan — repos, permissions, Day 1 checklist, architecture summary, first tasks, risks/approvals.
- **Primitive:** none required beyond the tool itself (this journey is intentionally NOT agentic in content, only in invocation).

### J2 — Ask a grounded question about my project (RAG)
- **Input:** free-text question, e.g. "why do we use this pattern in payments-platform?"
- **Agent behavior:** retrieves from the Knowledge Base (versioned docs: `architecture.md`, `runbook.md`, etc.) and answers **only** from retrieved context; if nothing relevant is retrieved, says so instead of guessing.
- **Output:** answer + citation to the source doc.
- **Primitive:** Knowledge Base (S3 Vectors) + Guardrails + the starter's Faithfulness evaluation.
- **New work:** this is the M2 RAG tool — not yet built.

### J3 — Track / mark an onboarding step done
- **Input:** "I finished cloning the repos."
- **Agent behavior:** calls `mark_step_done` (already shipped) and persists state; in a **later** session, recalls what's already done without re-asking.
- **Output:** updated checklist state, acknowledged in conversation.
- **Primitive:** AgentCore Memory (STM+LTM) for cross-session continuity — the "later session recall" half is new work; the tool call itself already exists.

### J4 — Request scoped access/action with approval
- **Input:** "I need write access to the payments repo."
- **Agent behavior:** checks the profile's `approvals_required` list. If listed, creates an approval request (HITL) — it never confirms access itself. The approver reviews and approves/denies; the agent only reports access as granted after that confirmation.
- **Output:** a pending-approval record visible to both employee and approver.
- **Primitive:** Guardrails (block unsafe auto-actions) + Observability (audit trail) + a real approval-state tool — **not yet built**; today this is a static Markdown list, not a stateful action.

## Out-of-scope boundary

Reconciled with the 3 hard constraints — none of the following violate "must be an onboarding
accelerator"; they're deliberately deferred for workshop-sandbox safety:
- Real provisioning in IAM Identity Center, GitHub/GitLab/CodeCommit, Jira/Slack/Teams/Confluence.
- Production-grade secrets management.
- Enterprise-wide guardrail policy authoring.
- Multi-tenant / multi-cohort backoffice.

## Source-of-truth data model

`profiles/*.yaml` and `projects/*.yaml` remain the **only** source of truth for permissions, repos, and
checklists — no shadow database, no agent-inferred permissions. The Knowledge Base ingests the
narrative `*.md` docs (architecture, runbooks, payments docs) for J2 **only**. The Knowledge Base must
never be the source for permissions data — J1 and J4 stay tool-based against the YAML, never RAG-based.
This is the concrete anti-hallucination boundary between "documents" and "facts." **Enforcement, not just
intent:** narrative docs (`runbook.md`, `architecture.md`) may mention access in prose (e.g. "you need
write access to deploy this service") — the system prompt instructs the agent that any access/permission
statement surfaced via J2 retrieval is informational context only, never an authorization decision; the
agent must redirect access questions to J4 rather than answer them from retrieved text.

## Data handled & retention

The assistant touches employee PII (name, email) and permission/approval data via Memory STM+LTM and the
profiles/projects YAML. This workshop MVP relies on AWS default encryption at rest and does not define an
explicit retention or deletion policy — that is an intentional gap for the sandbox, not a production-ready
answer, and must be resolved before any non-workshop use.

## Hallucination-tolerance policy per journey

| Journey | Tolerance |
|---------|-----------|
| J1 (plan generation) | Zero — tool-only, no generative content in repo/permission fields |
| J2 (RAG Q&A) | Zero for unsupported claims — must cite retrieved doc or decline; generative tolerance only in phrasing/summary style |
| J3 (track progress) | Zero — state mutation only through the tool, never inferred |
| J4 (approval request) | Zero on access-granted claims; some generative tolerance when explaining *why* approval is needed |

## AgentCore / Bedrock primitive mapping

| Quality need | Primitive | Verified shipped in starter? |
|---------------|-----------|-------------------------------|
| Continuity (J3) | AgentCore Memory STM+LTM | Yes — Bedrock stack |
| Grounded answers (J2) | Knowledge Base, S3 Vectors | Yes — Bedrock stack |
| Safety (J1/J4) | Guardrails | Yes — Bedrock stack |
| Approval workflow (J4) | Observability (audit trail) | Yes — Agent stack |
| Approval workflow (J4) | HITL approval **state** (custom tool) | **No** — not a shipped primitive; must be built |
| Measurable quality (esp. J2) | Evaluations (Faithfulness LLM-judge) | Yes — built-in eval system |
| Scoped real actions beyond demo (e.g. an actual IAM grant) | Gateway / Identity | **Not verified** as first-class stacks — optional add-on only, do not assume |

## Success metrics / KPIs

- **Time-to-first-task-start proxy:** time from intake to a complete plan (target: <2 min in demo).
- **% of J2 answers passing the Faithfulness eval** (target: 100% on the workshop test set — any failure is a defect to fix live, not an acceptable miss).
- **% of J4 requests correctly routed to approval vs. auto-approved**, checked against the profile's `approvals_required` list (target: 100% — zero false-auto-approvals is the safety KPI, weighted above speed). **Only measurable once the approval-state tool ships** (see MVP cut line below) — until then this is a target for the build, not a result to report.
- **Memory continuity check:** agent correctly recalls a prior session's completed steps in a new conversation (binary pass/fail).

## MVP vs. future cut line

**MVP (this workshop):**
- J1 — already shipped.
- J2 — new build (Knowledge Base + Faithfulness eval; this is "M2" from the AgentCore-redesign analysis).
- J3 — already shipped (cross-session recall via Memory is the new part).
- J4 — partial: build the approval **state** as a real tool/data structure; no notification/UI yet.

**Future (post-workshop roadmap):**
- Real notification integration for approvals (Slack/email).
- Gateway-based real provisioning.
- Multi-employee/cohort backoffice.
- Cost/latency-aware model routing.

## Local web UI delivery slice

The local web UI is the operator surface for the MVP. It supports the Bench domain described in
`BENCH_SPEC.md` while preserving the onboarding assistant's source-of-truth and safety boundaries.
This is a completion slice for the existing UI, not a replacement for the future AWS backoffice.

### UI requirements

The requirements below use stable IDs so implementation and end-to-end tests can refer to the same
contract.

#### Operator navigation and onboarding

- **UI-FR-001 — Navigate the operator surface.** A manager, People Lead, or enablement operator can
  reach the dashboard, employee review, onboarding, roles, tracks, tasks, responsibles, and AI
  knowledge from the web UI. Catalog areas must not depend on an undocumented URL.
- **UI-FR-002 — Create a bench onboarding record.** The operator can enter employee name and email,
  select a role/profile and track, optionally set the bench start date, and optionally upload the
  employee profile PDF. The UI validates required values and returns the operator to the created
  employee record.
- **UI-FR-003 — Show onboarding state.** The employee detail and operator review show the derived
  lifecycle state (`inactive`, `pre_bench`, or `active` for the local MVP), start date, assigned
  profile and track, progress, blockers, deadline risk, check-ins, plan, and available report.
- **UI-FR-004 — Maintain employee records.** The operator can edit a person's name, email, role,
  track, start date, and uploaded profile context, and can archive/remove a person with a clear
  confirmation. Removal must not silently delete durable reports or action history.

#### Catalog administration

- **UI-FR-005 — Maintain roles.** The operator can create, inline-edit, and delete a role/profile,
  including its summary, permission boundaries, and approval-required actions. Deletion is blocked
  with an actionable message while the role is assigned to an active employee.
- **UI-FR-006 — Maintain tracks.** The operator can create, edit, and delete a track, including
  duration and eligible roles. Deletion is blocked while the track is assigned to an active employee.
- **UI-FR-007 — Maintain tasks.** The operator can add, inline-edit, and delete a task template,
  including category, deadline, follow-up cadence, estimated effort, link, evidence requirement,
  approval flag, and reference contact. Changes must have an explicit effect on future assignments;
  existing employee task history must not be rewritten without confirmation.
- **UI-FR-008 — Maintain knowledge.** The operator can create, inline-edit, and delete mandatory
  courses, certifications, and suggested courses, including provider, URLs, tags, and notes.
- **UI-FR-009 — Maintain responsibles.** The operator can add, edit, and remove track responsibles
  and their notification role. The track detail shows the complete recipient list and the UI makes
  the report-delivery effect clear.

#### Progress and communication

- **UI-FR-010 — Update progress safely.** An operator or employee can update task status and evidence,
  complete AM/PM check-ins, and see deterministic progress verification. The UI never lets generated
  text override stored task state.
- **UI-FR-011 — Explain and preserve reports.** The UI can generate an EOD report, show its recipient
  list, preserve the report as a durable local record, and expose whether a proactive notification is
  pending or delivered. Changing the bench start date re-evaluates lifecycle notifications immediately.
- **UI-FR-012 — Surface approvals without granting access.** The employee and operator views show
  requested, pending, approved, or denied simulated access where that state exists. The UI must never
  claim that sensitive access was granted solely because a request was submitted, and this MVP does
  not perform real IAM or repository provisioning.
- **UI-FR-013 — Audit mutations.** Every create, edit, archive/delete, status change, date change,
  approval-state change, report generation, and notification-delivery action records actor, time,
  entity, action, and outcome. The relevant employee detail view exposes the action log.

### UI quality and acceptance bar

- **UI-NFR-001 — Local MVP boundary.** The UI runs locally with SQLite and simulated permissions;
  storage seams remain compatible with the architecture's later DynamoDB/API path.
- **UI-NFR-002 — Safety and data handling.** Permission data remains sourced from role/profile records,
  not generated text or knowledge suggestions. User-provided values are escaped in rendered HTML;
  destructive actions require confirmation and return an actionable validation error on failure.
- **UI-NFR-003 — End-to-end confidence.** Tests cover happy path, validation, protected deletion,
  inline edit, employee lifecycle maintenance, responsible assignment/removal, report generation,
  and changing the bench date through the UI. The acceptance run exercises every UI-FR at least once.
- **UI-NFR-004 — Trust boundary is explicit.** This local MVP is a trusted localhost operator tool;
  it is not an employee-facing or shared deployment and must not be exposed as one. Authentication,
  role-based web authorization, and per-employee information filtering are release blockers for any
  hosted/shared version and are outside this UI completion slice.

### Implementation audit at requirements update

The current implementation already covers dashboard, review, onboarding, task progress/check-ins,
reports, role CRUD, track CRUD, task CRUD, knowledge CRUD, responsible add/remove, and immediate
date-triggered notifications. The completion gaps are employee lifecycle CRUD, responsible edit,
discoverable navigation to tracks/tasks/responsibles, approval-state visibility, mutation audit
history, and end-to-end coverage for those paths. These gaps are the prioritized UI work implied by
the requirements above.
