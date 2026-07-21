# ADR 0004: Teams bot as a thin channel over the Bench service

- **Status:** accepted
- **Date:** 2026-07-13

## Context

A second MVP (`teams-bot/`, formerly BenchCoach) proved the Teams channel: a Python bot on
the Microsoft 365 Agents SDK (Teams SDK v2), registered in the Endava tenant, running
locally via dev tunnels, deployable to Azure App Service with Managed Identity. Its first
iteration duplicated bench logic in-process (in-memory sessions, hardcoded plan) and called
Bedrock directly with boto3 from the bot.

Meanwhile the Bench service (this repo) owns the real logic: relational catalog,
deterministic verification, LangGraph daily cycle, EOD reports — but had no channel to
people, and Teams delivery was simulated as a file.

## Decision

The bot is a **thin channel adapter**; the Bench service is the only brain.

- The bot holds **no domain logic, no persistent state and no AWS credentials**. boto3 is
  removed from the bot; **Bedrock is called only by the Bench service** (the Bedrock access
  discovered in the bot MVP — SSO profile, `bedrock:InvokeModel`, us-west-2 — moves to the
  service's environment).
- Contract: the bot POSTs to the service's `/api/v1` (FastAPI router in `bench/api.py`):
  `POST /chat {employee_email, text, conversation_id}` for freeform,
  plus explicit endpoints (`/onboard`, `/plan`, `/tasks`, `/checkin`, `/report`, `/catalog`)
  for commands. Replies are Markdown strings the bot posts verbatim.
- **Identity:** the bot resolves the Teams user's corporate email via the conversation
  members API (`TeamsChannelAccount.email`; manifest already has the `identity` permission)
  and sends it on every request. That email is the join key to `people` in the bench DB.
- The service-side intent router decides: known command → deterministic tool/graph;
  anything else → the agentic graph (Bedrock) with a deterministic fallback when AWS is
  unavailable, so the channel works end-to-end without credentials.
- EOD delivery to responsibles will use **proactive bot messages** (replaces the earlier
  Teams-webhook plan in the AWS access checklist).

## Consequences

- One brain: fixing logic in `bench/` fixes CLI, web UI and Teams at once. The bot survives
  restarts and scale-out because state lives in the service DB.
- The bot keeps only ephemeral UX state (guided intake step), which is channel concern.
- The service must be reachable from the bot (localhost in dev; App Runner/ALB later).
- Secrets hygiene: the bot's `.env` (Entra CLIENT_SECRET) stays out of git; the copied
  `teams-bot/` ships an `.env.example` only.

## UI completion amendment (2026-07-20)

Actor context, lifecycle rules, audit records, report metadata, and notification status remain owned
by the Bench service and shared tools. The web UI and Teams adapter do not interpret channel-local
delivery as domain state. Report save, notification queued/pending, delivered, and failed outcomes are
independent projections; a Teams message cannot imply access provisioning or report delivery until the
service records that outcome.
