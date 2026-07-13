# Context for AI agents

This file is meant to be read by AI agents, coding assistants, or code-generation tools before modifying this repository.

## Project context

We're building an agentic MVP for developer onboarding. The end goal is for a new developer to be productive from day 1.

The team wants to learn and use:

- AWS.
- Amazon Bedrock.
- Amazon Bedrock AgentCore.
- Strands Agents.
- Agent-with-tools patterns.
- AWS-native architectures with low initial dependence on external SaaS.

## Important constraints

1. Prioritize AWS-native solutions.
2. Do not assume real integrations with Confluence, Jira, Slack or GitHub in the initial MVP.
3. Model permissions, projects and profiles as versioned YAML.
   **Bench-domain exception (this branch):** the Bench catalog (roles, tracks, tasks) lives
   in SQLite with a seed migration instead of YAML, to support the backoffice ABM — see
   `docs/adr/0003-relational-catalog-sqlite.md`. The onboarding workshop domain (`agent/`,
   `profiles/`, `projects/`) keeps versioned YAML.
4. Design so that a backoffice can later exist where employee + profile + project are entered.
5. Keep the code simple for workshop purposes.
6. Avoid automating real permissions without explicit approval.
7. Every change must preserve the ability to run the agent locally.

## Bench domain (feature/bench branch)

A second domain: assistant for people on Endava's Bench (courses, certifications, daily
goals, EOD reports). Spec: `docs/BENCH_SPEC.md`; ADRs: `docs/adr/`. Gated by
`BENCH_ENABLED=1`. Engines: deterministic LangGraph cycle (`bench/graph.py`), agentic
LangGraph (`bench/agent_graph.py`), Strands agent (`bench/strands_agent.py`). Dev storage
is SQLite (`bench/db.py` + `bench/seed.py`); production swaps to DynamoDB behind the same
functions in `bench/tools/`.

## Functional domain

The expected flow is:

1. A manager or admin selects an employee.
2. Selects a profile, e.g. `backend-dev`.
3. Selects a project, e.g. `payments-platform`.
4. The agent loads the profile and project.
5. The agent generates a personalized onboarding plan.
6. The agent can record progress.

## Relevant files

- `profiles/*.yaml`: defines profiles, expected permissions and base tasks.
- `projects/*.yaml`: defines projects, repositories, architecture and specific tasks.
- `agent/app.py`: agent entry point.
- `agent/tools/*.py`: tools invokable by the agent.
- `docs/ARCHITECTURE.md`: target architecture.
- `accelerator/INTEGRATION_PLAN.md`: how to use the AWS sample.

## Implementation style

- Simple Python.
- Small functions.
- Explicit tools.
- Readable YAML.
- Markdown for documentation.
- Minimal but useful tests.

## Expected future evolutions

- Connect to AgentCore Runtime.
- Add DynamoDB for real tracking.
- Add S3 as a knowledge source.
- Add IAM Identity Center for real permissions.
- Add a backoffice with Amplify, App Runner or FastAPI.
- Add guardrails and observability.

## Instruction for AI agents

When modifying this repo, do not turn it into a complex production solution prematurely. It must first work as learning and workshop material. Prefer small, explainable changes oriented toward teaching AgentCore and Strands Agents.
