# DayOne Bench Assistant

DayOne Bench is an agentic assistant for people between client engagements. It
helps Bench engineers follow a role- and track-specific plan, complete daily
goals, record evidence, and receive grounded study suggestions. People Leads and
Resourcing receive durable end-of-day status and deadline-risk reports.

The canonical product definition is [`docs/BENCH_SPEC.md`](docs/BENCH_SPEC.md).
It owns the Bench domain’s journeys, data model, anti-hallucination boundary,
engine split, integrations, and MVP cut line.

## What works today

The local MVP runs without AWS:

- Deterministic Bench plan generation from an employee, profile, and track.
- SQLite-backed catalog and per-person state.
- AM/PM check-ins, deterministic goal verification, and durable EOD reports.
- Lifecycle nudges and a Teams proactive-notification queue.
- Profile-matched knowledge and study suggestions.
- Local web UI, CLI, API, and tests.

LLMs may summarize or explain grounded facts, but they do not invent courses,
permissions, deadlines, or completion outcomes. SQLite is the local source of
truth. DynamoDB, Bedrock, AgentCore Runtime, Knowledge Bases, EventBridge, and
the repository feedback bot are production or future integrations described in
the product specification.

## Architecture

```text
CLI / web UI / API / Teams thin channel
                     |
                     v
              Shared Bench tools
                     |
        SQLite catalog and person state
                     |
       +-------------+-------------+
       |                           |
   Strands conversation      LangGraph daily cycle
   (optional AWS)            (local deterministic path)
```

The Teams bot resolves the user identity and forwards requests to the service;
it does not own domain logic, state, or AWS credentials. The Bench track
references role/profile permissions but never grants access.

## Repository structure

```text
bench/                              Bench domain, tools, DB, API, UI, graphs
agent/                              Original onboarding workshop agent
teams-bot/                          Thin Microsoft Teams channel adapter
profiles/                           Declarative role/profile definitions
projects/                           Declarative project definitions
docs/BENCH_SPEC.md                  Canonical Bench product specification
docs/adr/                           Architecture decisions
_bmad/                              Child-local team BMad integration
_bmad-output/                       Planning, stories, specs, sprint status
tests/                              Unit, API, UI, adapter, and regression tests
```

## Local setup

Install [uv](https://docs.astral.sh/uv/) and use Python 3.11 or newer:

```bash
uv sync --dev
uv run pytest
```

The test suite is the primary local validation command. Optional UI dependencies
can be installed with:

```bash
uv sync --group ui
```

Do not commit `.env` files, tokens, AWS credentials, or local runtime data.
Use `.env.example` as a reference only. AWS-backed optional dependencies and
access requirements are documented in
[`docs/BENCH_AWS_ACCESS_CHECKLIST.md`](docs/BENCH_AWS_ACCESS_CHECKLIST.md).

## Run Bench locally

Enable the Bench domain for CLI commands:

```bash
BENCH_ENABLED=1 uv run python -m bench.seed
BENCH_ENABLED=1 uv run python -m bench.app start \
  --employee "Ada Lovelace" \
  --email ada@example.com \
  --profile backend-dev \
  --track aws-backend-track
BENCH_ENABLED=1 uv run python -m bench.app tasks --email ada@example.com
```

Run the daily cycle:

```bash
BENCH_ENABLED=1 uv run python -m bench.graph \
  --email ada@example.com --period am --planned "Course module 3"
BENCH_ENABLED=1 uv run python -m bench.graph \
  --email ada@example.com --period pm \
  --task "1=in_progress:course at 45%"
```

Run the local web UI:

```bash
BENCH_ENABLED=1 uv run --group ui uvicorn bench.webapp:app --reload
```

Open `http://127.0.0.1:8000`. Local state is stored under
`.local-progress/`, including `bench.db` and durable report files; this data is
ignored by Git.

## Development workflow

All story work starts from `feature/bench` in a dedicated branch and worktree:

```bash
git worktree add ../worktrees/dayone/<story-key> \
  -b feat/bench-<story-key> feature/bench
```

The lifecycle is: create or load the story, validate it, implement it, run
`uv run pytest`, review it, and open a draft PR targeting `feature/bench`.
See [`docs/development-workflow.md`](docs/development-workflow.md) for the
authoritative workflow and PR requirements.

## Child-local BMad

This repository is the BMad project root. Team configuration, resolver scripts,
manifests, durable specs, stories, sprint status, and memory artifacts live
under `_bmad/` and `_bmad-output/`. BMad skill definitions remain an external,
environment-installed prerequisite; the repository does not vendor the hub’s
`.agents/` tree or personal installer configuration.

From the child root, validate the integration with:

```bash
python3 _bmad/scripts/resolve_config.py --project-root "$PWD"
python3 _bmad/scripts/resolve_customization.py \
  --skill <installed-skill-path> --key workflow
```

Resolved project paths must remain inside this repository. Full prerequisite
and safety guidance is in [`docs/bmad-workflow.md`](docs/bmad-workflow.md).

## Security and data boundaries

- SQLite is authoritative for local Bench catalog and person facts.
- DynamoDB is a separate future storage path; do not mirror or hybrid-route data.
- Profile permissions are facts, not access grants made by a Bench track.
- User-provided values must be escaped at presentation boundaries.
- Destructive actions require confirmation and preserve history where specified.
- The local service is a trusted-localhost tool, not a hosted authorization boundary.
- Teams holds no domain state or AWS credentials.
- Never commit credentials, tokens, `.env` files, personal BMad config, caches,
  virtual environments, or `.local-progress/` data.

## Authoritative references

- [Bench product specification](docs/BENCH_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Architecture decisions](docs/adr/)
- [Development workflow](docs/development-workflow.md)
- [BMad child-local workflow](docs/bmad-workflow.md)
- [Original README](README.original.md)
