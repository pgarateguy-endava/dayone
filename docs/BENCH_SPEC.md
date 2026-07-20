# Bench Assistant — Product Spec

> **Ownership.** This document owns the product definition of the **Bench domain**: personas,
> journeys, data model and MVP cut line. It does **not** own the onboarding product
> (see `PRODUCT_SPEC.md`), instructional design (`PEDAGOGY_SPEC.md`) or infrastructure
> (`ARCHITECTURE.md`, `adr/`). The Bench domain lives in the `feature/bench` branch and reuses
> the onboarding MVP's explicit-tools architecture, but its catalog + state live in a
> **relational SQLite store** rather than YAML (see `adr/0003-relational-catalog-sqlite.md`).

## 1. Problem

At Endava, people between client engagements go to **Bench**. During bench, they are expected
to take courses, pursue certifications, update their professional profile for upcoming clients,
and build desirable portfolio experience. Today this is loosely tracked and depends on manual
follow-up by People Leads / Resourcing.

The Bench Assistant is an agentic application that:

1. Generates a **personalized bench plan** from the person's role/profile + an assigned **track**
   (mandatory courses, certification options, profile-update tasks, portfolio project ideas).
2. Runs a **daily cycle**: twice-a-day check-ins, verification of daily goals, and an
   **end-of-day report** sent to the responsible people (People Lead, Resourcing).
3. Enforces **deadlines** and flags people at risk of missing them.
4. (Complementary) Reviews the person's practice repositories and gives feedback
   (CodeRabbit-style), linked to the person's bench record.

## 2. Personas

| Persona | Needs |
|---|---|
| **Bench engineer** | Clear plan, daily goals, quick check-ins, feedback on practice work. |
| **People Lead / Resourcing (responsible)** | EOD status per person, deadline risk flags, zero manual chasing. |
| **Capability / Discipline lead** | Aggregate view: which certs/courses the bench population is progressing on. (Future) |

## 3. Journeys

### B1 — Bench plan generation (MVP, deterministic)
Input: `employee + profile (role) + track`. Output: Markdown bench plan with mandatory courses,
certification path, daily goals, profile-update tasks, portfolio project suggestions, deadlines
and responsibles. Same anti-hallucination stance as onboarding J1: **the plan is produced by a
deterministic tool, never free-form LLM text.** The relational catalog (SQLite, ADR 0003) is
the source of truth.

### B2 — Daily cycle (MVP, LangGraph)
A stateful pipeline that runs twice a day per bench person:

```text
load_state → collect_check_in → verify_goals → (PM run only) build_eod_report → notify_responsibles
```

- **AM check-in**: person declares what they will work on today (goals proposed from the track).
- **PM check-in**: person declares what was completed, with evidence links (course progress,
  commit URLs, profile diff).
- **verify_goals**: deterministic comparison of declared completions vs. the track's daily goals;
  the LLM (when enabled) only summarizes, it does not decide completion.
- **EOD report**: Markdown report to the responsibles: progress %, goals met/missed, deadline
  risk, next-day goals. Always written to `.local-progress/reports/` (durable record) **and**
  queued as a Teams proactive message for each responsible who has talked to the bot — the bot's
  poll loop delivers it (`bench/notify.py` `queue_notification`, kind `eod_report`).

**Two complementary proactive mechanisms** — keep them distinct:

1. **Scheduled daily cycle** (`bench/graph.py`): the fixed AM/PM pipeline above; per-task
   `follow_up` cadence (`twice_daily`/`daily`/`weekly`/`biweekly`) drives what `verify_goals`
   chases each day. Triggered per person (CLI, `/api/v1/checkin`, or — in production —
   EventBridge twice daily).
2. **Lifecycle nudge engine** (`bench/notify.py`): status-driven proactive messages keyed off
   `bench_start_date` (`computed_status` → `inactive`/`pre_bench`/`active`):
   `pre_bench_greeting` (2–10 days before start) → `planning_prompt` (day before) →
   `kickoff` (on start) → weekly `progress_check`. Evaluated by a 60s scheduler in the web app
   and re-fired immediately when a start date changes. This is what actually reaches people on
   Teams today; the AM/PM cycle is the reporting spine for responsibles.

### B3 — Grounded Q&A over Endava profile documentation (future, RAG)
Bedrock Knowledge Base over Endava profile/role documentation so the person can ask
"what does a Senior Backend profile need to show?" Answers cite documents. Mirrors onboarding J2.

### B4 — Repo feedback bot (complementary, future)
A reviewer identity that knows which repos belong to each bench person, analyzes them and
attaches feedback to the person's bench record. Explicitly out of MVP; specified so the data
model already carries `practice_repos[]` per person.

### B6 — Teams as the conversation channel (built)
The `teams-bot/` app (Microsoft 365 Agents SDK) is a thin adapter: it resolves the user's
corporate email, registers the conversation reference, and forwards **every** message to the
service's `POST /api/v1/chat` (all intent routing is service-side). The service leads with the
agentic graph (Bedrock) and falls back to deterministic keyword handling when AWS is absent.
Proactive messages (lifecycle nudges + EOD reports) are delivered by the bot's poll loop over
`/api/v1/notifications/pending`. The bot holds no domain logic, state, or AWS credentials.
See `docs/adr/0004-teams-bot-thin-channel.md`.

### B5 — Role-based access mapping (reuses onboarding)
Bench people keep role-scoped accesses. This reuses the role/profile definitions
(`profiles` + `profile_permissions` + `profile_approvals` in SQLite; editable in the Roles ABM)
untouched by the track — the bench track never grants access; it only *references* the profile.

### B7 — Knowledge base + profile-matched study suggestions (built)
A curated `knowledge` catalog (mandatory courses, certifications, courses — each with provider,
URL, completion-registration URL and CSV tags), editable in the AI Knowledge ABM. `suggest_for_profile`
matches items to the person's extracted Endava Profile text by tag substring (mandatory items
always apply); the agent narrates the result but never invents courses. This feeds the `kickoff`
message and the `get_study_suggestions` tool. Today it is deterministic tag matching; the Bedrock
Knowledge Base (B3) is the future backend for grounded, cited answers.

## 4. Data model

The entire Bench catalog **and** per-person state live in a **relational SQLite database**
(`bench/db.py`, file `.local-progress/bench.db`), seeded idempotently by `bench/seed.py`.
This supersedes the earlier YAML sketch — see `adr/0003-relational-catalog-sqlite.md` for why
(one-to-many tasks with their own deadline/follow-up/contacts, and per-person task status that
can't live on a shared template). Onboarding (on `main`) keeps its YAML; only Bench moved.

Catalog (editable in the web ABMs):
- `profiles` + `profile_permissions` + `profile_approvals` — role, access, approvals. **Source of
  truth for access.** The bench track only references a profile; it never grants access.
- `tracks` ⇄ `profiles` (via `track_profiles`) — which roles a track fits.
- `tasks` (1→N `task_contacts`) — catalog task templates: `category`, `due_date`, `follow_up`
  cadence, `est_hours`, `link`, `evidence_required`, `requires_approval`.
- `responsibles` — who receives the EOD report for a track.
- `knowledge` — mandatory courses / certifications / courses with tags (feeds B7).

Per-person state:
- `people` — assignment (profile, track), `bench_start_date` (**the activation trigger**),
  extracted `profile_text` from the uploaded Endava Profile PDF.
- `person_tasks` — each person's task instance with its own `status`, `evidence`, timestamps.
- `check_ins` — the AM/PM journal.
- `conversation_refs` + `notifications` — the Teams proactive-contact queue and audit log.

Production path: migrate table-by-table to DynamoDB (`ONBOARDING_STATE_TABLE` pattern); the
`bench/tools/*` function signatures are the swap seam. EOD reports also persist to
`.local-progress/reports/` as a durable record alongside Teams delivery.

## 5. Anti-hallucination boundary

| Data | Source of truth | LLM may… |
|---|---|---|
| Permissions/access | `profiles`/`profile_permissions` (SQLite) | never invent or confirm |
| Courses, certs, deadlines, goals | `tracks`/`tasks` (SQLite) | never invent; only render/summarize |
| Goal completion | deterministic `verify_goals` | summarize outcome only |
| Study suggestions | deterministic `suggest_for_profile` over `knowledge` (B7) | narrate matches; never add items |
| Study advice, explanations | LLM (B3 grounded when KB exists) | generate, with citations when KB is live |

## 6. Engine decision (hybrid)

- **Strands agent** for the conversational side (person asks questions, requests plan,
  marks steps) — consistent with the workshop material. See `bench/strands_agent.py`.
- **LangGraph** for the scheduled daily cycle (fixed steps, explicit state machine) —
  see `bench/graph.py` and `adr/0002-hybrid-strands-langgraph.md`.
- Both deploy to **AgentCore Runtime** (framework-agnostic). Scheduling via EventBridge.

## 7. Integrations

| Integration | MVP | Production |
|---|---|---|
| Teams | proactive bot messages via the queue + poll loop (nudges & EOD); report file always kept | hosted service reachable by the bot; managed identity |
| Endava profile docs | local `docs/endava/` placeholders + uploaded profile PDF text | S3 + Bedrock Knowledge Base |
| Course progress | self-declared in check-in | LMS API if available; else keep self-declared + evidence links |
| Repos (B4) | `practice_repos[]` field only | reviewer bot + AgentCore Memory |

## 8. MVP cut line

**In (works today, no AWS):** B1 plan, B2 daily cycle with SQLite state and file-based reports,
B5 via existing profiles, B6 Teams channel + proactive queue (nudges & EOD queued for delivery),
B7 knowledge base + profile-matched suggestions, web back-office, `/api/v1` with token auth,
tests, CLI.
**Out (needs AWS):** Bedrock LLM in the graph (deterministic fallback otherwise), AgentCore
Runtime/Memory, DynamoDB, KB/RAG (B3), EventBridge scheduling (a 60s in-process scheduler stands
in), repo bot (B4), and hosting the service where the bot can reach it for a real Teams pilot.
See `BENCH_AWS_ACCESS_CHECKLIST.md` for exactly what to request.

## 9. KPIs

- % of bench people with an active plan and same-day check-ins.
- Daily goal completion rate; deadline-at-risk flags raised before the deadline (not after).
- Time from bench entry to updated profile.
- Responsible time saved (no manual chasing; EOD report is the single update).
