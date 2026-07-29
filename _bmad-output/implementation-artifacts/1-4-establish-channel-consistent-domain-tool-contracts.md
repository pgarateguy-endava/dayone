---
baseline_commit: f50f870
---

# Story 1.4: Establish channel-consistent domain tool contracts

Status: done

## Story

As a developer maintaining Bench,
I want shared domain-shaped tool operations for reads and mutations,
so that the UI, API, Teams, CLI, and scheduled flows cannot diverge.

## Acceptance Criteria

1. **Shared ownership:** Given a behavior is required by more than one channel, when it is implemented, then business rules and SQLite access live behind `bench/tools` and storage seams, while web routes/templates contain only projection and HTTP composition.
2. **Full-page response contract:** Given a successful full-page create or person-level mutation, when the UI responds, then it uses POST → 303 → canonical page and the canonical page reads the committed state.
3. **Inline response contract:** Given a successful inline mutation, when the UI responds, then it returns only the stable targeted fragment after server confirmation; failed input remains available with an actionable associated error, and cancel restores read mode.
4. **Storage-neutral contract:** Given a later storage adapter is substituted, when a tool operation is called, then its domain-shaped input/output and error contract remain unchanged; no route, template, API handler, CLI command, or Teams adapter depends on SQLite-specific details.
5. **Cross-channel parity:** Contract tests exercise the same representative operations through web, JSON API, CLI, and the scheduled/Teams entry points, asserting equal persisted facts, actor/audit behavior, normalization, and response semantics. Teams remains a thin HTTP client of the service API; it must not acquire domain logic or persistent state.
6. **Regression safety:** Existing deterministic verification, AM/PM graph behavior, report save/outbox reconciliation, notification lifecycle, actor propagation, stable person identity, and action-history behavior remain intact. `uv run pytest` passes.

## Scope and boundaries

In scope:

- Define or consolidate the smallest shared domain-tool contracts needed by current duplicated channel workflows: person onboarding/date/task/check-in/report operations, catalog reads/mutations, knowledge CRUD, notification/report status operations, and stable history/state projections.
- Make channel adapters translate their native input into those contracts and translate returned domain results/errors into HTML redirects/fragments, JSON, CLI output, or Teams messages.
- Normalize email and resolve actor context at the shared boundary. Preserve the public email-based channel inputs while using stable `person_id` internally wherever available.
- Establish explicit result/error shapes sufficient for both full-page and inline UI paths; do not make callers inspect SQLite rows or parse generated prose to determine success.

Out of scope:

- Completing DynamoDB schema/parity or enabling a complete DynamoDB-only runtime. The current partial adapter is transitional and must not be expanded into a hybrid design.
- New UI journeys, navigation, accessibility redesign, hosted authentication, real provisioning, real Teams delivery guarantees, or report/notification state-machine redesign.
- Rewriting the Strands conversation engine or LangGraph daily-cycle architecture. They may consume the same tools where required.
- Broad refactoring unrelated to a duplicated/shared behavior.

## Tasks / Subtasks

- [x] Inventory existing channel entry points and duplicate business/persistence logic (AC: 1, 4, 5)
  - [x] Compare `bench/webapp.py`, `bench/api.py`, `bench/app.py`, `bench/webapp.py` scheduler/lifespan, and `teams-bot/src/app.py` against the current `bench/tools` modules.
  - [x] Record each operation’s current inputs, returned facts, errors, actor boundary, transaction boundary, and response type before moving code.
  - [x] Keep the inventory implementation-focused; do not alter requirements or architecture documents.
- [x] Define the shared domain contract seam (AC: 1, 4)
  - [x] Reuse existing tools and transaction helpers before adding modules; avoid a second parallel service layer.
  - [x] Use domain-shaped dictionaries/dataclasses/typed results consistent with the existing Python 3.11+ codebase, with stable identifiers and explicit success/error semantics.
  - [x] Ensure storage details (`sqlite3.Connection`, SQL, row objects, DynamoDB keys/conditions) do not escape tool/storage modules.
  - [x] Preserve one complete backend choice per runtime; do not route one operation family to DynamoDB and another to SQLite as a new pattern.
- [x] Refactor web/API/CLI/scheduled adapters to the seam (AC: 1–5)
  - [x] Keep FastAPI routes responsible for HTTP parsing, status codes, redirects, JSON, and HTML fragment rendering only.
  - [x] Use POST → 303 for full-page creates/person mutations and stable fragment IDs plus server-confirmed fragment responses for inline mutations.
  - [x] Keep API JSON contracts backward-compatible for the Teams bot unless a compatibility-preserving translation is added at the API boundary.
  - [x] Keep CLI commands as argument parsing and presentation around the same tools; preserve `BENCH_ENABLED` and actor context behavior.
  - [x] Keep scheduled notification evaluation and Teams delivery as channel concerns around service-owned notification operations; Teams must not write Bench state.
- [x] Preserve cross-cutting invariants (AC: 4, 6)
  - [x] Use `BENCH_ACTOR`, with visible `local-operator` fallback, at channel boundaries; do not pass channel-local actor names into tools.
  - [x] Keep successful mutation plus success audit transaction-coupled where possible, and never let audit failure mask the original rejected error.
  - [x] Keep email normalization/editability separate from stable person identity and preserve task, check-in, report, notification, conversation, and audit history.
  - [x] Keep report save, notification queued/pending/delivered/failed, and simulated approval projections distinct; never return “sent” or “granted” for a saved/queued/simulated state.
- [x] Add contract and regression tests (AC: 2–6)
  - [x] Add focused shared-tool contract tests using isolated temporary SQLite databases and reopening connections to verify persisted facts.
  - [x] Exercise the minimum parity matrix below: onboard/person mutation, task/status mutation, report save, catalog/knowledge mutation, and notification delivery/status.
  - [x] Test web 303 and canonical-page behavior, inline stable-target fragment behavior, retained invalid input/error behavior, and API JSON compatibility.
  - [x] Test CLI and scheduled/Teams boundaries without AWS credentials or live Teams dependencies; assert Teams remains an API client.
  - [x] Run focused tests, then `uv run pytest`.

### Review Findings

- [x] [Review][Patch] Complete the shared contract seam for all required operations — named contracts now own onboarding, person/task/date/check-in/report operations, notification scheduling, chat mutations, catalog task/knowledge mutations, and committed serializable projections. [bench/tools/contracts.py; bench/api.py; bench/webapp.py; bench/app.py]
- [x] [Review][Patch] Translate `DomainError` consistently at every channel boundary — API errors are stable 4xx responses, web errors use global or stable inline fragments, and CLI errors are safe nonzero results. [bench/api.py; bench/webapp.py; bench/app.py]
- [x] [Review][Patch] Replace blanket built-in exception classification with operation-scoped translation; unexpected exception types retain their original traceback. [bench/tools/contracts.py]
- [x] [Review][Patch] Enforce a strict shared email contract, including malformed identities and responsible-contact normalization. [bench/tools/contracts.py; bench/tools/catalog.py]
- [x] [Review][Patch] Align onboarding notification behavior through the shared operation and retain a retryable pending projection if reconciliation fails. [bench/tools/contracts.py; bench/api.py; bench/webapp.py]
- [x] [Review][Patch] Keep diagnostic domain messages separate from safe channel-facing messages. [bench/tools/contracts.py; bench/api.py]
- [x] [Review][Patch] Enforce JSON-serializable `DomainResult` projections at the shared boundary. [bench/tools/contracts.py]
- [x] [Review][Patch] Expand focused contract coverage for CLI, graph/check-in/report, API/web parity, normalization, safe errors, reopened SQLite state, and Teams persistence isolation. [tests/test_contracts.py]
- [x] [Review][Defer] Preserve instantiated task history on catalog deletion — current deletion removes `person_tasks` before deleting the template, which is a pre-existing history-safety violation outside this diff. [bench/tools/catalog.py:166-178] — deferred, pre-existing
- [x] [Review][Defer] Normalize and uniquely constrain responsible contacts — current schema/tooling permits case-insensitive duplicates on one track, a pre-existing catalog invariant gap outside this diff. [bench/db.py:62-67; bench/tools/catalog.py:257-264] — deferred, pre-existing

## Dev Notes

### Current implementation intelligence

- `bench/webapp.py` is the primary projection layer but currently contains repeated orchestration: onboarding calls `start_bench()` and notification generation, person routes call state/report tools directly, and catalog/knowledge routes translate form fields and render rows. Keep HTML helpers and route paths stable while moving any rule/persistence decision into tools.
- `bench/api.py` is the service boundary consumed by Teams. It currently routes onboarding, task updates, check-ins, plans, reports, notifications, and chat, but it also assembles channel-specific replies and performs some direct orchestration. Preserve the documented `/api/v1` JSON-in/`{"reply": "<markdown>"}` behavior unless a compatibility translation is explicit.
- `bench/app.py` already establishes `actor_context()` around CLI dispatch and calls the same state/catalog/report tools. Do not create CLI-only implementations.
- `teams-bot/src/app.py` intentionally owns only Teams identity resolution, ephemeral conversation mapping, HTTP calls, and message delivery. It must not import `bench` or access SQLite.
- Scheduled behavior currently lives in `bench/webapp.py` lifespan/proactive loop and `bench/notify.py`; notification generation/evaluation remains service-owned and delivery acknowledgement remains explicit.
- Existing shared modules are `bench/tools/state.py`, `catalog.py`, `knowledge.py`, `eod_report.py`, `audit.py`, `verify_goals.py`, and `generate_bench_plan.py`, plus `bench/notify.py` for notification operations. Extend the nearest existing seam rather than introducing duplicate helpers.

### Non-negotiable contract invariants

- One domain operation has one rule implementation, regardless of caller.
- A successful mutation means the authoritative state and its required audit record are committed.
- A channel may change presentation, but never the operation’s meaning, identity normalization, validation, or error classification.
- A domain result is serializable committed state; a domain error is stable actionable semantics.
- Storage replacement changes implementation behind the seam, not callers or channel behavior.
- Parity tests compare persisted facts and domain outcomes, not identical HTML, Markdown, or CLI wording.

### Required operation-contract properties

Each shared operation should make these properties explicit in its public result/error behavior:

- Inputs are normalized/validated once at the shared boundary; email keys are case-insensitive and stable person identity is preferred for internal history/state queries.
- Successful results represent committed SQLite state, not the submitted form values or optimistic client state.
- Missing targets, invalid state transitions, protected deletion, duplicate identity, and dependency conflicts have actionable typed/domain errors that channels can map consistently.
- Mutations identify the operation with stable verb-led names and preserve actor/audit semantics established by Stories 1.1–1.3.
- Reads return serializable domain projections, not `sqlite3.Row`, cursors, connections, SQL fragments, or backend-specific keys.
- A future adapter can implement the same operation without requiring routes/templates to know consistency, key, or query-language details.

Prefer a small explicit contract vocabulary rather than unstructured booleans or exception-string matching:

- Successful writes return a serializable `DomainResult`-style projection containing the operation name, committed entity/person identifiers, and the persisted values needed by the caller. A plain typed dictionary/dataclass is sufficient; do not introduce a framework solely for this wrapper.
- Reads return serializable domain projections with stable keys and no database objects.
- Expected domain failures use one shared base error (for example `DomainError`) with specific subclasses or stable error codes for `not_found`, `validation`, `conflict`, and `protected`/dependency failures. Include safe field/target details for channel rendering, but never include SQL, credentials, tokens, or report bodies.
- Channel adapters map those stable codes to HTTP status/JSON, retained form errors/fragments, or CLI/Teams messages. They must not branch on SQLite exception text or infer success from a `None` return.
- Unexpected infrastructure errors propagate through the existing boundary handling and must not be relabelled as user validation errors.

### Minimum parity matrix

The implementation must cover these operations through the indicated boundaries. “Same facts” means the shared tool result and reopened SQLite state agree; response text is allowed to differ by channel.

| Operation | Web | JSON API | CLI | Scheduled / Teams | Parity assertions |
|---|---:|---:|---:|---:|---|
| Onboard or mutate a person | ✓ | ✓ | ✓ | Teams via API | normalized identity, stable `person_id`, actor, audit, committed task instances |
| Update task/status or check-in | ✓ | ✓ | ✓ | Teams via API; scheduled graph where applicable | persisted status/evidence/check-in, deterministic result, audit |
| Save/report projection | ✓ | ✓ | ✓ | scheduled PM graph | report metadata/path and notification state remain distinct |
| Catalog or knowledge mutation | ✓ | representative API/tool contract | ✓ or direct tool harness | not a Teams-owned operation | validation, protected/dependency errors, persisted catalog facts, audit |
| Notification status/delivery acknowledgement | status projection | ✓ | representative tool/CLI harness | scheduled generation + Teams delivery acknowledgement | queued/pending/delivered state, idempotency, actor/audit, no claim of delivery before acknowledgement |

The Teams column means the Teams bot calls the service API and remains free of domain persistence. The scheduled column means the scheduler/graph invokes the same service-owned operation; it does not create a parallel mutation implementation. Where a channel has no user-facing command for an operation, test the shared tool through that channel’s actual boundary or an explicitly named adapter harness rather than inventing a new channel feature.

### Boundary and edge-case requirements

Contract tests must also cover:

- repeated mutation and delivery requests;
- blank, mixed-case, malformed, Unicode, and oversized inputs;
- unknown, archived, protected, and already-processed targets;
- stale inline responses and server-confirmed re-reads;
- report/outbox and notification failures at each external boundary;
- missing/invalid API credentials, actor fallback, inherited actor isolation, and channel timeouts;
- unavailable or unsupported storage adapters without hybrid fallback;
- deterministic results and audit ordering under repeated or concurrent calls.

Every case must produce either the same committed domain outcome or the same stable domain error across applicable channels. No adapter may convert an uncertain or partial operation into a successful response.

### Pre-mortem completion gates

Before marking the story complete, verify:

- Each changed operation has one identifiable tool/storage owner and no duplicate channel rule.
- Existing API and Teams contracts remain compatible through automated tests.
- Parity tests compare reopened committed state, stable domain errors, actor, and audit—not identical presentation text.
- Injected failures cannot produce a false success, partial mutation, or misleading fragment.
- Repeated requests have idempotent or explicitly documented semantics.
- No DynamoDB parity, hosted auth, or unrelated UI redesign entered the implementation.

Do not force every operation into one generic “execute command” abstraction. The goal is a small set of clear domain seams, not a framework. Keep pure projections (`computed_status`, `verify_progress`, plan/report generation) separate from mutations and keep generated Markdown as a read-only projection.

### Response semantics

- Full-page form actions that create or mutate a person return `RedirectResponse(..., status_code=303)` to a canonical route after the shared operation commits. The GET reloads committed data.
- Inline catalog/knowledge row actions return the row/fragment for the stable target ID after commit. Save returns read mode; cancel re-reads the original row; validation failure returns the same target with retained safe input and an associated error.
- htmx enhancement must not create a second persistence path. The no-JavaScript/normal form behavior remains understandable and server-authoritative.
- Do not assume a 3xx response will process htmx response headers; use the existing project response pattern and keep fragment responses 2xx where htmx headers/target swaps are required.

### Architecture compliance

- AD-1/AD-2: Bench stays a parallel domain; SQLite owns local Bench truth.
- AD-4/AD-5: Strands/LangGraph responsibilities remain explicit; all channels share deterministic tools.
- AD-8/AD-9: lifecycle/archive, stable identity, actor, and audit behavior remain tool-level concerns.
- AD-10/AD-11: report/notification state machines stay independent and UI response contracts stay predictable.
- AD-13: protected deletion and history safety remain domain rules, not route conditionals.
- AD-15: storage replacement changes the adapter, not channel contracts.

### File and structure guardrails

Likely updates (confirm against current code before editing):

- UPDATE `bench/tools/state.py`, `bench/tools/catalog.py`, `bench/tools/knowledge.py`, `bench/tools/eod_report.py`, `bench/tools/audit.py`, and/or `bench/notify.py` only where a missing shared contract or transaction-safe result requires it.
- UPDATE `bench/webapp.py`, `bench/api.py`, and `bench/app.py` to become thin adapters; preserve routes, API paths, CLI names, and established HTML fragment IDs where practical.
- UPDATE `teams-bot/src/app.py` only if a service API compatibility boundary requires it; do not add domain persistence or logic there.
- NEW/UPDATE focused tests alongside existing `tests/test_api.py`, `tests/test_webapp.py`, `tests/test_bench.py`, `tests/test_notify.py`, and a new contract-focused test module if useful.

Do not modify `docs/`, requirements, UX, architecture, ADR, or test documents as part of implementation without explicit authorization. Do not add dependencies. Never commit credentials, tokens, `.env`, `.local-progress/`, or AWS/Teams runtime data.

### Testing requirements

Use the child repository’s canonical command:

```bash
uv run pytest
```

Tests must use isolated temporary progress/database paths, avoid developer-local state, and assert persisted rows after reopening the database. Include at least one forced failure at the tool boundary to prove rollback/error translation, one actor propagation assertion per representative channel boundary, and one parity assertion showing that equivalent operations produce equivalent persisted facts. API/UI tests must not require AWS credentials; Teams tests should use a mocked HTTP service/client boundary.

### Previous story intelligence

Story 1.3 established append-only audit storage/querying and hardened atomicity across state, catalog, knowledge, notification, report, and identity mutations. It also explicitly deferred complete DynamoDB parity and retained the current partial adapter as a compatibility baseline. Reuse `append_audit()` with the active transaction; do not reintroduce separate connections or claim hybrid DynamoDB behavior is complete.

Story 1.2 established `actor_context()`/`current_actor()` with configured values, blank fallback, nested/exception restoration, async isolation, and boundary non-inheritance. Resolve actor context at each channel boundary and do not leak a test override or invent channel-local actors.

Story 1.1 established stable `person_id`, normalized email support, lifecycle/archive fields, and history-preserving identity migration. Preserve email-based external inputs for compatibility, but do not use mutable email as the historical identity key.

### Git intelligence

The current child branch is `feature/bench`; recent work includes the child-local BMad bootstrap and the Story 1.3 audit implementation. Story 1.3’s implementation favored small shared helpers, existing stdlib/framework dependencies, isolated tests, and explicit deferred-work notes. Work on this story in a dedicated worktree/branch according to `docs/development-workflow.md`; do not implement directly on `feature/bench`.

### Latest technical specifics

- FastAPI supports declaring and returning explicit response status codes; use the existing `RedirectResponse` pattern for 303 full-page mutations. Source: [FastAPI response status codes](https://fastapi.tiangolo.com/tutorial/response-status-code/) and [custom responses](https://fastapi.tiangolo.com/advanced/custom-response/).
- htmx swaps server-returned HTML into the selected target according to `hx-target`/`hx-swap`; its documentation also notes that 3xx responses do not process htmx response headers in the normal way. Keep the project’s 2xx fragment contract for inline actions and do not use optimistic client state. Sources: [htmx documentation](https://htmx.org/docs/), [`hx-target`](https://htmx.org/attributes/hx-target/), [`hx-swap`](https://htmx.org/attributes/hx-swap/).
- Python’s current SQLite documentation recommends explicit transaction control and notes that connection context managers commit/roll back but do not replace explicit connection closing. Preserve the repository’s connection helper and active-connection transaction pattern; do not open a second connection inside a mutation. Source: [Python `sqlite3` documentation](https://docs.python.org/3/library/sqlite3.html).

### Project context reference

Follow [docs/development-workflow.md](../../docs/development-workflow.md), [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), [docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md](../../docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md), [docs/spec-review-dayone-bench-ui/SPEC.md](../../docs/spec-review-dayone-bench-ui/SPEC.md), [docs/adr/0001-bench-as-parallel-domain.md](../../docs/adr/0001-bench-as-parallel-domain.md), [docs/adr/0002-hybrid-strands-langgraph.md](../../docs/adr/0002-hybrid-strands-langgraph.md), [docs/adr/0003-relational-catalog-sqlite.md](../../docs/adr/0003-relational-catalog-sqlite.md), and [docs/adr/0004-teams-bot-thin-channel.md](../../docs/adr/0004-teams-bot-thin-channel.md). Preserve the canonical six-step foundation sequence, localhost trust boundary, SQLite authority, shared `bench/tools` ownership, explicit actor fallback, response contracts, and no-credentials rule.

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Backlog selection: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Story foundation: `_bmad-output/planning-artifacts/epics.md`, Epic 1 / Story 1.4
- Architecture and UX guardrails: `docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md`, `docs/spec-review-dayone-bench-ui/SPEC.md`

### Implementation Plan

- Added a small `bench.tools.contracts` seam with serializable `DomainResult`, stable `DomainError` classifications, and one-time email normalization.
- Routed representative web, API, CLI, and scheduler mutations through the seam while preserving existing channel response formats and Teams HTTP-only ownership.
- Added isolated contract tests for result/error semantics, normalization, API error translation, web/API committed-fact parity, and Teams persistence isolation.
- Preserved the existing SQLite transaction, actor, audit, report, notification, and backend-selection implementations; no new dependency or DynamoDB behavior was introduced.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story created from the canonical Epic 1.4 contract, current source tree, Stories 1.1–1.3, recent Git history, child workflow instructions, and primary framework documentation.
- Added `bench/tools/contracts.py` with stable serializable results, expected domain-error translation, and normalized email validation.
- Refactored representative web/API/CLI/scheduled paths to call the shared contract seam without changing public API or Teams response formats.
- Added `tests/test_contracts.py` covering result/error behavior, normalization, web/API parity, and the Teams no-persistence boundary.
- Focused contract tests: `uv run --group ui pytest tests/test_contracts.py -q` — 9 passed, 1 warning.
- Full regression suite: `uv run pytest -q` — 77 passed, 1 warning.
- UI-enabled regression suite: `uv run --group ui pytest -q` — 77 passed, 1 warning.
- Adversarial code review: all 8 patch findings applied; 2 pre-existing findings deferred in `deferred-work.md`.
- No credentials, tokens, `.env` files, runtime data, or new dependencies were added.

### File List

- `_bmad-output/implementation-artifacts/1-4-establish-channel-consistent-domain-tool-contracts.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `bench/tools/contracts.py`
- `bench/api.py`
- `bench/app.py`
- `bench/webapp.py`
- `tests/test_contracts.py`
- `_bmad-output/implementation-artifacts/deferred-work.md`

## Change Log

- 2026-07-28: Implemented shared domain result/error contracts and routed representative channel operations through the seam; added contract/parity tests.
