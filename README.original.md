# Onboarding AgentCore Workshop

[![ci](https://github.com/rivadaviam/dayone/actions/workflows/ci.yml/badge.svg)](https://github.com/rivadaviam/dayone/actions/workflows/ci.yml)

Workshop MVP for building an agentic developer-onboarding assistant using **Amazon Bedrock AgentCore**, **Strands Agents** and native AWS services.

The goal of this repo is to serve as a starting point for the team to learn how to build, run and deploy an agent that, given an employee + profile + project, generates an onboarding plan, explains repositories, lists expected permissions and tracks progress.

> **Status: simulated vs. what you'll build.** This repo starts as **Lab 1** — a plain Python plan
> generator that runs **without** the Strands SDK. The real agent (Strands + Bedrock) is **Lab 2**
> and the AWS accelerator is **Lab 3**. Permissions, repos and state are **simulated** until later
> phases. Full labs guide: [`docs/WORKSHOP_LABS.md`](docs/WORKSHOP_LABS.md).

## Desired Product

The output of this project is a developer-focused onboarding assistant application that helps new team members understand the context of a project in no time so the ramp up is smooth and quick. The assistant should guide a developer through the practical information they need when joining a project, such as required technical setup, local environment configuration, project setup instructions, required credentials, access to tools and boards, and links to relevant project documentation.

Because onboarding needs can vary from project to project, the assistant should be flexible and driven by project-specific context. For example, one project might require a specific Node.js version, AWS access and Jira board access, while another project might require a different setup, credentials or documentation.

## MVP objectives

- Learn AgentCore Runtime and Strands Agents with a realistic case.
- Reduce external dependencies like Confluence/Jira/Slack during the MVP.
- Use local versioned documentation in the repo and/or S3.
- Model permissions and onboarding as declarative templates.
- Prepare the path for a backoffice UI where a manager selects employee, profile and project.

## MVP architecture

```text
Future backoffice / CLI
        |
        v
Strands Agent
        |
        +--> tools/load_profile.py
        +--> tools/load_project.py
        +--> tools/generate_plan.py
        +--> tools/track_progress.py
        |
        v
Future AgentCore Runtime
        |
        +--> Future DynamoDB: onboarding state
        +--> Future S3: versioned internal docs
        +--> Future IAM Identity Center: real permissions
        +--> Future CodeCommit/GitHub: real repos
```

## Structure

```text
.
├── agent/                         # Strands agent code
│   ├── app.py                      # Minimal agent
│   ├── config.py                   # Configuration
│   ├── prompts.py                  # System prompts
│   └── tools/                      # Simulated local tools
├── bench/                          # Bench domain (feature/bench): DB, tools, graphs, web UI
├── profiles/                       # Declarative onboarding profiles
├── projects/                       # Declarative projects
├── docs/                           # Objectives, context and decisions (incl. docs/adr/)
├── accelerator/                    # Integration with the AWS sample
├── scripts/                        # Setup/demo scripts
├── infra/backoffice/               # Placeholder for the future backoffice
└── tests/                          # Minimal tests
```

## Local quickstart

Using [uv](https://docs.astral.sh/uv/) (recommended — creates the venv and installs everything):

```bash
uv sync --dev
uv run python -m agent.app --employee "Ada Lovelace" --email ada@example.com --profile backend-dev --project payments-platform
```

<details>
<summary>Classic pip/venv alternative</summary>

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m agent.app --employee "Ada Lovelace" --email ada@example.com --profile backend-dev --project payments-platform
```

</details>

Expected output: an onboarding plan in Markdown with repos, permissions, checklist and first steps.

## Strands path (real agent, optional)

The local path above (`agent/app.py`) runs **without** the SDK. For a **Strands agent** to orchestrate
the same tools (Lab 2), use [`agent/strands_agent.py`](agent/strands_agent.py):

```bash
# 1) Enable the SDK (uncomment strands-agents and bedrock-agentcore in requirements.txt)
pip install strands-agents bedrock-agentcore

# 2) Configure AWS + Bedrock
cp .env.example .env          # set AWS_REGION and BEDROCK_MODEL_ID (requires model access)

# 3) Run the real agent
python -m agent.strands_agent --employee "Ada Lovelace" --email ada@example.com \
  --profile backend-dev --project payments-platform
```

The tools are the **same** functions from `agent/tools/`, now wrapped as Strands `@tool`.
Tool contract details (read / generation / write / dangerous) in
[`docs/AGENTCORE_STRANDS_NOTES.md`](docs/AGENTCORE_STRANDS_NOTES.md).

## Using the AWS accelerator

This workshop is designed to coexist with the official accelerator `aws-samples/sample-strands-agentcore-starter`.

```bash
bash accelerator/clone_aws_starter.sh
```

Then check `accelerator/INTEGRATION_PLAN.md` to decide whether to:

1. Use this repo as the domain layer and copy its tools/prompts into the starter.
2. Use the starter as the full-stack base and migrate this MVP into its `agent/` folder.
3. Keep both: starter for infrastructure and this repo for workshop exercises.

## Suggested roadmap

### Phase 1: Local workshop
- Run the local agent.
- Understand Strands tools and prompts.
- Add a new profile and project.
- Generate an onboarding plan.

### Phase 2: AgentCore
- Package the agent for AgentCore Runtime.
- Configure observability.
- Invoke per session.
- Compare local vs. managed runtime.

### Phase 3: Backoffice
- Create a minimal UI: employee, email, profile, project.
- Persist state in DynamoDB.
- Generate a checklist per employee.

### Phase 4: Real permissions
- Connect IAM Identity Center.
- Map profiles to permission sets.
- Approve sensitive actions human-in-the-loop.

## Bench domain (branch `feature/bench`)

A second, real-world domain built on the same architecture: an assistant for people on
**Endava's Bench** (courses, certifications, daily goals, profile updates, EOD reports to
responsibles). Spec: [`docs/BENCH_SPEC.md`](docs/BENCH_SPEC.md) · ADRs: [`docs/adr/`](docs/adr) ·
AWS accesses to request: [`docs/BENCH_AWS_ACCESS_CHECKLIST.md`](docs/BENCH_AWS_ACCESS_CHECKLIST.md).

Bench is behind a feature flag: set `BENCH_ENABLED=1` (env or `.env`). The catalog
(roles, tracks, tasks with deadlines / follow-up frequency / contacts) is relational,
in SQLite, seeded with dummy data (ADR 0003).

```bash
BENCH_ENABLED=1 uv run python -m bench.seed    # load dummy catalog (first time)

# assign a person to bench and get the plan (deterministic, no AWS)
BENCH_ENABLED=1 uv run python -m bench.app start --employee "Ada Lovelace" \
  --email ada@example.com --profile backend-dev --track aws-backend-track
BENCH_ENABLED=1 uv run python -m bench.app tasks --email ada@example.com

# daily cycle as a LangGraph workflow (AM and PM check-ins, EOD report)
BENCH_ENABLED=1 uv run python -m bench.graph --email ada@example.com --period am --planned "Course module 3"
BENCH_ENABLED=1 uv run python -m bench.graph --email ada@example.com --period pm --task "1=in_progress:course at 45%"
```

Engine split (ADR 0002): **Strands** for conversation (`bench/strands_agent.py`, optional,
needs AWS) and **LangGraph** for the scheduled daily cycle (`bench/graph.py`, runs local).
There is also an **agentic LangGraph** variant where the LLM is bound to the bench tools
(`bench/agent_graph.py`, `ToolNode` + `bind_tools`, needs AWS: `uv sync --extra agentic`).

### Teams channel (teams-bot/)

`teams-bot/` is a Microsoft Teams bot (M365 Agents SDK) acting as a **thin channel** over
this service (ADR 0004): it resolves the user's email and forwards everything to
`/api/v1` (`bench/api.py`) — no domain logic, no state, no AWS credentials in the bot.
Run the service (`uvicorn bench.webapp:app`), then F5 the bot from VS Code with the
M365 Agents Toolkit (see `teams-bot/README.md`); set `BENCH_BACKEND_URL` if not localhost.

### Dev web UI (SQLite state)

```bash
uv sync --group ui
BENCH_ENABLED=1 uv run --group ui uvicorn bench.webapp:app --reload
# open http://127.0.0.1:8000
```

Dashboard for responsibles, person cycle (plan, AM/PM check-ins, EOD report) and a catalog
editor for roles and tracks. Dev state lives in SQLite (`.local-progress/bench.db`);
production swaps the same functions to DynamoDB.

## Design principle

Onboarding must be declarative:

```yaml
employee: ada@example.com
profile: backend-dev
project: payments-platform
```

The system automatically derives repos, permissions, tasks, documentation and next steps.
