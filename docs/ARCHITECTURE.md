# Target architecture

## Bench local architecture amendment (2026-07-20)

The Bench domain is distinct from the older YAML onboarding sketch below. Bench catalog and state use
SQLite as the local source of truth behind `bench/tools`; FastAPI/htmx, JSON API, Teams, CLI, and
scheduled flows are thin channels over those seams. The localhost MVP uses simulated permissions and
the explicit `BENCH_ACTOR` context with visible `local-operator` fallback. It is not a hosted or
employee-facing backoffice.

Bench lifecycle, audit, report metadata, and notification state are durable domain facts. Successful
mutations and their audit records commit atomically. A stable `person_id` owns history while email is
editable. Reports remain file-backed for the MVP, with SQLite metadata and recipient snapshots; saved,
queued/pending, delivered, and failed notification states remain independent. A later DynamoDB/API
path replaces storage behind the tool seam without moving persistence or business rules into channels.

## Local MVP

The local MVP uses YAML files and Python tools to teach the pattern:

```text
CLI / future backoffice
  -> agent.app
  -> load_profile
  -> load_project
  -> generate_onboarding_plan
  -> track_progress
```

This flow lets us validate the domain without creating real permissions.

## Target AWS architecture

```text
Web backoffice
  -> API backend
  -> AgentCore Runtime with a Strands agent
  -> AWS tools
       -> IAM Identity Center
       -> CodeCommit / Git provider
       -> DynamoDB
       -> S3 docs
       -> EventBridge
       -> CloudWatch / X-Ray
```

## Components

### Backoffice

Interface for managers or admins. Minimum fields:

- Employee name.
- Email.
- Profile.
- Project or set of projects.
- Start date.
- Optional buddy.

### AgentCore Runtime

Hosts the agent and/or tools. AgentCore Runtime handles scaling, session management, security isolation and managed infrastructure, letting the team focus on the agent experience.

### Strands Agent

Holds the reasoning, system prompt and tools.

### DynamoDB

State persistence:

- Onboarding created.
- Completed steps.
- Errors.
- Pending approvals.

### S3

Versioned internal documentation, ready for indexing:

- Project guides.
- Runbooks.
- Diagrams.
- FAQs.

### IAM Identity Center

Real assignment of groups and permission sets in later phases.

## MVP decisions

1. Use YAML as the initial contract.
2. Keep permissions simulated until the flow is validated.
3. Design every action as an independent tool.
4. Let the agent explain what it would do before doing it.
5. Require human approval for sensitive access.

## Open questions

- Which Git provider will be used in production?
- Will projects be one-to-one, or can an employee join multiple projects?
- Which system will be the source of truth for employees?
- Which actions require approval from the manager, tech lead or security?
- How will day-1 productivity be measured?
