# Bench Assistant — Product Spec

> **Ownership.** This document owns the product definition of the **Bench domain**: personas,
> journeys, data model and MVP cut line. It does **not** own the onboarding product
> (see `PRODUCT_SPEC.md`), instructional design (`PEDAGOGY_SPEC.md`) or infrastructure
> (`ARCHITECTURE.md`, `adr/`). The Bench domain lives in the `feature/bench` branch and reuses
> the declarative YAML + explicit-tools architecture of the onboarding MVP.

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
deterministic tool, never free-form LLM text.** YAML is the source of truth.

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
  risk, next-day goals. MVP: written to `.local-progress/reports/`. Production: Teams message.

### B3 — Grounded Q&A over Endava profile documentation (future, RAG)
Bedrock Knowledge Base over Endava profile/role documentation so the person can ask
"what does a Senior Backend profile need to show?" Answers cite documents. Mirrors onboarding J2.

### B4 — Repo feedback bot (complementary, future)
A reviewer identity that knows which repos belong to each bench person, analyzes them and
attaches feedback to the person's bench record. Explicitly out of MVP; specified so the data
model already carries `practice_repos[]` per person.

### B5 — Role-based access mapping (reuses onboarding)
Bench people keep role-scoped accesses. This reuses `profiles/*.yaml` `permissions` +
`approvals_required` untouched — the bench track never grants access; it only *references*
the profile.

## 4. Data model

- `profiles/*.yaml` — **reused as-is** (role, permissions, approvals). Source of truth for access.
- `tracks/*.yaml` — new. Bench track: mandatory courses, certification options, daily goals,
  profile tasks, portfolio projects, deadlines, responsibles. Schema in `tracks/README.md`.
- `.local-progress/bench_<email>.json` — MVP state: assignment, check-ins, goal events.
  Production: DynamoDB (`ONBOARDING_STATE_TABLE` pattern).
- `.local-progress/reports/` — MVP stand-in for Teams notifications.

## 5. Anti-hallucination boundary

| Data | Source of truth | LLM may… |
|---|---|---|
| Permissions/access | `profiles/*.yaml` | never invent or confirm |
| Courses, certs, deadlines, goals | `tracks/*.yaml` | never invent; only render/summarize |
| Goal completion | deterministic `verify_goals` | summarize outcome only |
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
| Teams | report file on disk | Graph API / Incoming Webhook from the notify node |
| Endava profile docs | local `docs/endava/` placeholders | S3 + Bedrock Knowledge Base |
| Course progress | self-declared in check-in | LMS API if available; else keep self-declared + evidence links |
| Repos (B4) | `practice_repos[]` field only | reviewer bot + AgentCore Memory |

## 8. MVP cut line

**In (works today, no AWS):** B1 plan, B2 daily cycle with local state and file-based reports,
B5 via existing profiles, tests, CLI.
**Out (needs AWS):** Bedrock LLM in the graph, AgentCore Runtime/Memory, DynamoDB, KB/RAG (B3),
Teams delivery, EventBridge scheduling, repo bot (B4).
See `BENCH_AWS_ACCESS_CHECKLIST.md` for exactly what to request.

## 9. KPIs

- % of bench people with an active plan and same-day check-ins.
- Daily goal completion rate; deadline-at-risk flags raised before the deadline (not after).
- Time from bench entry to updated profile.
- Responsible time saved (no manual chasing; EOD report is the single update).
