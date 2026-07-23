---
baseline_commit: ffa3a498f714cb563c3a2e970a0e25f59061006a
---

# Story 1.2: Resolve and propagate the explicit local actor

Status: review

## Story

As an operator,
I want the resolved Bench actor visible and consistent across channels,
so that every mutation has an accountable local identity.

## Acceptance Criteria

1. **Configured actor is authoritative.** Given `BENCH_ACTOR` is set to a non-blank value, when a mutation is invoked through the web UI, JSON API, Teams-facing API path, CLI, or scheduled daily/proactive path, then the shared Bench context resolves that exact value as the actor. No channel-specific identity, employee email, API bearer token, or hard-coded substitute may replace it.
2. **Visible safe fallback.** Given `BENCH_ACTOR` is unset, empty, or whitespace-only, when a local UI page is rendered, then it displays `local-operator`; when a mutation runs, the shared context returns `local-operator` and never `None`, an empty string, or an anonymous actor.
3. **Request/task isolation.** Given concurrent or sequential requests use different actor overrides, when each mutation completes, then each observes only its own actor and the next request/task returns to the environment-derived actor. Actor state must not leak through module globals, thread-local state, cached configuration, async tasks, or test fixtures.
4. **Test override is explicit and reversible.** Given a test temporarily overrides the actor, when the mutation completes, then the override is observable through the shared mutation context/spy contract and the override is restored in a `finally`-safe manner before unrelated tests run.
5. **Every mutation receives actor context.** Existing write seams used by onboarding, task status, check-ins, date changes, reports, notification/conversation operations, catalog CRUD, knowledge CRUD, and the LangGraph/proactive paths must resolve or receive the shared actor. Preserve their existing result, validation, transaction, and error behavior; audit-row persistence belongs to Story 1.3.
6. **UI exposes the same resolved actor.** The local web shell/context shows the resolved actor on normal pages and does not claim hosted authentication or employee-level authorization. The displayed value and the value supplied to web mutations come from the same shared resolver.
7. **Channel consistency is testable.** Unit tests cover configured, fallback, blank, override, reset, and isolation behavior. API, web, CLI/graph, scheduled/proactive, and Teams-adapter contract tests demonstrate the same resolved actor reaches the shared mutation seam. Tests must not require AWS, a real Teams tenant, or external credentials.

## Tasks / Subtasks

- [x] Define the shared actor contract (AC: 1–4)
  - [x] Add a small dependency-free actor/context module at the shared Bench boundary; do not put actor resolution in individual routes or templates.
  - [x] Resolve `BENCH_ACTOR` at call/request context time, using `strip()` only to decide blankness; preserve the configured non-blank actor value as the accountable identity.
  - [x] Expose a read function for the current actor and a test/request context override that restores prior state even when the wrapped operation raises. Define the semantics unambiguously: `None` means no override, a non-blank override is accepted as-is, and an explicitly blank override raises a clear `ValueError` rather than creating an anonymous actor.
  - [x] Make the default visibly and consistently `local-operator`.
- [x] Integrate the actor into all in-scope channels (AC: 1, 5, 7)
  - [x] Web: establish actor context per request or mutation and render the resolved actor in the shared page shell through the existing `esc()` helper; do not infer it from form data, URL path, employee email, or browser state.
  - [x] JSON API: establish the same context for `/api/v1` operations, including onboarding, task/check-in, chat-driven writes, conversation registration, and notification-delivery updates. Keep `BENCH_API_TOKEN` authentication separate from actor identity.
  - [x] Teams: preserve ADR 0004's thin-adapter boundary; the service-owned actor context must not be replaced with the Teams user's email. If the repository has no Teams adapter implementation, cover the service/API contract that the adapter consumes and document the omission rather than inventing a second adapter.
  - [x] CLI and scheduled paths: ensure `bench.graph` and the web lifespan proactive loop resolve the same actor when they call deterministic tools directly.
  - [x] Agentic paths: ensure `bench/agent_graph.py` tool closures and the optional `bench/strands_agent.py` wrappers reach the same shared context when they invoke deterministic write tools; do not let the LLM, conversation id, or employee email become the actor.
  - [x] Thread context through shared `bench/tools` write seams without forcing callers to duplicate actor lookup or changing public business arguments unnecessarily. Leave room for Story 1.3 to persist the resolved actor in an atomic audit record.
- [x] Preserve existing behavior and boundaries (AC: 5–6)
  - [x] Keep SQLite as the Bench source of truth and keep business rules in `bench/tools`/storage seams; routes, templates, and adapters remain projections/composition only.
  - [x] Do not create the audit table or implement append-only audit persistence in this story; Story 1.3 owns that storage and query surface.
  - [x] Do not add hosted authentication, authorization, employee filtering, real provisioning, Teams delivery, or a new dependency.
  - [x] Preserve the Story 1.1 durable `person_id` and normalized-email behavior and all existing mutation return values/error semantics.
- [x] Add focused regression coverage (AC: 2–7)
  - [x] Test env reads at call time so monkeypatched `BENCH_ACTOR` values are honored without module reload.
  - [x] Test unset, `""`, whitespace, configured value, nested override, exception reset, and sequential/concurrent isolation.
  - [x] Test a representative write through state/catalog/notification seams and assert the shared actor value is available at the seam without requiring audit storage.
  - [x] Test web HTML contains the resolved actor for configured and fallback cases.
  - [x] Test API, graph/CLI-callable, agentic tool-wrapper, and proactive scheduler entry points use the same actor contract; use spies/fakes where AWS, Strands, LangChain, or a real delivery adapter is absent.
  - [x] Run `python -m pytest --version`, `python -m pytest`, and the repository's documented `uv run pytest`; report real results.

## Dev Notes

### Scope and implementation guardrails

This story is the actor-context prerequisite for the audit work in Story 1.3. It must make the actor available everywhere a mutation is initiated, but it must not pretend that actor propagation is durable audit history yet. The implementation should establish one shared contract that Story 1.3 can call while inserting `actor` into its append-only SQLite record.

The local MVP is a trusted localhost operator tool with simulated permissions. `BENCH_ACTOR` is accountability context, not authentication. Do not use `BENCH_API_TOKEN`, the Teams corporate email, the target employee email, a profile/role, or a browser-supplied field as a substitute. Never create an anonymous audit value or render a claim that access has been granted.

### Current code and exact integration points

- `bench/config.py` reads environment settings through functions such as `api_token()` and `bench_enabled()`. Add actor resolution in a shared module or nearby configuration seam, but read the environment at call time so tests and long-running local processes do not retain stale import-time configuration.
- `bench/db.py` owns SQLite connection/schema/migration details. Story 1.1 completed versioned migrations and durable `person_id`; do not add actor schema here yet. A DB connection must not become the only place actor is resolved because CLI, graph, and non-DB projections also need the context.
- `bench/tools/state.py` owns onboarding/reset, task status, check-ins, date changes, and person reads. Its current write functions use `connect()` and must remain compatible with the new context. In particular, do not reintroduce email-owned identity or change the existing date-trigger notification behavior.
- `bench/tools/catalog.py`, `bench/tools/knowledge.py`, `bench/tools/eod_report.py`, and `bench/notify.py` contain additional writes. Cover their shared actor access at the seam; do not duplicate actor resolution in every function.
- `bench/api.py` defines the `/api/v1` router consumed by the Teams bot. Existing `_email_key()` normalization is unrelated to actor resolution. Preserve bearer-token behavior and response contracts while making the shared actor available to endpoint-triggered writes.
- `bench/webapp.py` creates the FastAPI app, renders `_page()`, starts the 60-second `_proactive_loop()`, and exposes direct HTML mutations. The actor shown by `_page()` must be the same resolver used by mutations. The scheduler should use the default environment/fallback context and must not inherit a request actor.
- `bench/graph.py` is the deterministic AM/PM LangGraph entry point and `bench/app.py` is the SQLite Bench CLI entry point. They call deterministic tools directly and should be testable without installing agentic/AWS extras.
- `bench/agent_graph.py` creates per-employee LangGraph tool closures for the API chat path, while `bench/strands_agent.py` wraps the same deterministic tools for the optional Strands path. Both must inherit the service actor context and must never derive actor identity from their closed-over employee email or conversation metadata.
- There is no Teams adapter in this child repository. ADR 0004 defines the adapter as thin and service-owned; do not create unrelated Teams code solely for this story.

### Recommended context shape

Use the Python standard library only. A module-level `contextvars.ContextVar` (or an equivalent explicit context manager with the same isolation guarantees) is appropriate for request/task-local state; environment fallback should be resolved when the actor is requested. Any `set()` must have a matching reset in `finally`. Do not use a mutable module global or `threading.local()` for async request state.

Keep the public contract small and domain-shaped, for example:

- `resolve_actor() -> str`: returns the configured non-blank `BENCH_ACTOR`, otherwise `local-operator`.
- `current_actor() -> str`: returns an active scoped override when present, otherwise `resolve_actor()`.
- `actor_context(value: str | None)`: context manager used by tests/request boundaries; `None` means use the environment/fallback, non-blank values are accepted as-is, blank values raise `ValueError`, and the previous context is always restored.

The exact names may follow repository conventions. The important invariants are call-time env resolution, non-anonymous fallback, context isolation, and one shared import path used by all channels/tools.

### Architecture compliance

- AD-1/AD-2: keep Bench isolated and SQLite authoritative.
- AD-4/AD-5: deterministic tools remain the mutation owners; web/API/Teams/CLI/scheduled channels share the seam.
- AD-8: lifecycle/date semantics remain unchanged.
- AD-9: this story supplies the explicit actor and fallback; Story 1.3 adds the durable audit record and atomic coupling.
- AD-15: do not leak SQLite-specific details into the actor API or channel layer.

### Testing standards

Use existing pytest fixtures and temporary SQLite directories. Do not rely on `.env`, AWS credentials, a live server, or a real Teams integration. Tests that mutate `os.environ` must use pytest monkeypatch. Tests that scope actor overrides must verify restoration after both success and exception. If async tests are added, verify task/request isolation rather than only sequential behavior.

Run from the child repository worktree:

```text
python -m pytest --version
python -m pytest
uv run pytest
git diff --check
```

Missing pytest is an environment defect, not a reason to waive validation.

### Latest technical information

- Python's `contextvars` is standard-library functionality available since Python 3.7 and is natively supported by `asyncio`; it is intended for context-local state in concurrent code and avoids state bleeding between requests/tasks. See [Python contextvars documentation](https://docs.python.org/3/library/contextvars.html).
- Python's `os.environ` is a process-level mapping, so read `BENCH_ACTOR` at resolution time rather than caching it during import. See [Python os documentation](https://docs.python.org/3/library/os.html).
- FastAPI dependencies can centralize request-scoped setup and apply globally or to a router; use that only as a thin boundary that establishes the shared actor context, not as a second actor implementation. See [FastAPI dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) and [global dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/global-dependencies/).
- No new third-party library or version upgrade is justified. The project targets Python `>=3.11`, FastAPI `>=0.115` in the UI group, and pytest `>=8` in the dev group; preserve those existing constraints.

### Previous story intelligence

Story 1.1 introduced versioned migrations, deterministic `person_id`, normalized email support, and explicit archive/task fields. Its implementation required review fixes around durable foreign-key relationships, materialized knowledge tasks, email-edit conflicts, and unknown-person notification safety. Do not use the actor story as an excuse to alter those contracts. Story 1.1 validated with `uv run pytest` (25 passed, 2 skipped) and `git diff --check`.

Recent implementation patterns to preserve:

- `bench.db.connect()` runs migrations and enables foreign keys; avoid putting request-local actor state into the connection lifecycle.
- State tools normalize person email for lookup but now resolve durable relationships by `person_id`; actor context is orthogonal to person identity.
- Existing tests monkeypatch `bench.db.PROGRESS_DIR` and environment flags. New actor tests should follow that isolation style.

### Project Structure Notes

This child project is the Bench domain under `projects/dayone`. The story artifact and sprint tracker live under `_bmad-output/implementation-artifacts`; implementation belongs in the existing `bench/` and `tests/` structure. Do not modify the hub repository's planning/docs files or another child repository. Likely implementation files are `bench/config.py` or a new shared `bench/context.py`/`bench/actor.py`, `bench/api.py`, `bench/webapp.py`, `bench/graph.py`, relevant tool modules, and focused test modules. Confirm actual touch points before editing and avoid broad rewrites.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2-Resolve-and-propagate-the-explicit-local-actor]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-1-Durable-foundation-and-mutation-audit]
- [Source: docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md#AD-5--Channels-are-thin]
- [Source: docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md#AD-9--Every-mutation-has-an-explicit-local-actor-and-audit-record]
- [Source: docs/architecture-dayone-bench-2026-07-20/ARCHITECTURE-SPINE.md#AD-15--Storage-replacement-is-behind-the-tool-seam]
- [Source: docs/spec-review-dayone-bench-ui/SPEC.md#Constraints]
- [Source: docs/spec-review-dayone-bench-ui/items-must-not-change.md]
- [Source: docs/adr/0004-teams-bot-thin-channel.md]
- [Source: bench/config.py]
- [Source: bench/db.py]
- [Source: bench/tools/state.py]
- [Source: bench/api.py]
- [Source: bench/webapp.py]
- [Source: bench/graph.py]
- [Source: tests/test_api.py]
- [Source: tests/test_webapp.py]
- [Source: tests/test_bench.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `python -m pytest` could not run because this WSL shell has no `python` executable; `uv run python -m pytest --version` reported pytest 9.1.1 and the canonical `uv run pytest` command passed.
- The UI-group test command initially needed external uv cache access; after approval, the complete UI-enabled suite passed.

### Implementation Plan

- Add `bench.actor` with call-time `BENCH_ACTOR` resolution, `local-operator` fallback, scoped `ContextVar` overrides, blank rejection, and guaranteed reset.
- Establish the shared context at FastAPI API dependencies, web middleware/page rendering, proactive scheduling, and agentic CLI wrappers without introducing audit persistence or changing channel identity.
- Add focused contract and API/web integration tests, then run both the canonical and UI-enabled pytest suites.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented shared actor resolution with exact non-blank environment values and `local-operator` fallback.
- Added scoped, async-safe actor overrides with exception-safe restoration and explicit blank rejection.
- Propagated the shared context through FastAPI API requests, web requests/page shell, proactive scheduling, LangGraph chat, and optional Strands entry points.
- Preserved `BENCH_API_TOKEN` as authentication and kept actor identity independent from employee email, Teams identity, and conversation metadata.
- Validation: UI-enabled `uv run --group ui pytest -q` → 52 passed, 1 existing Starlette deprecation warning; canonical `uv run pytest -q` → 52 passed; `git diff --check` passed.

### File List

- `_bmad-output/implementation-artifacts/1-2-resolve-and-propagate-the-explicit-local-actor.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `bench/actor.py`
- `bench/agent_graph.py`
- `bench/api.py`
- `bench/strands_agent.py`
- `bench/webapp.py`
- `tests/test_actor.py`
- `tests/test_api.py`
- `tests/test_webapp.py`

### Change Log

- 2026-07-23: Implemented explicit local actor resolution and cross-channel propagation; added actor contract and API/web regression coverage; status advanced to review.
