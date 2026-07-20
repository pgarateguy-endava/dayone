# BenchCoach — Teams bot (thin channel)

This is the **Microsoft Teams channel** for the Bench Assistant. It is a deliberately *thin
adapter* (see `../docs/adr/0004-teams-bot-thin-channel.md`): it holds **no domain logic, no
persistent state, and no AWS credentials**. The Bench service (`bench/api.py`) is the only brain;
Bedrock is called only by the service.

## What the bot does

1. **Resolves the user's corporate email** from the Teams roster (`TeamsChannelAccount.email`;
   the manifest requests the `identity` permission). Falls back to `email you@endava.com` if the
   roster lookup is unavailable. This email is the join key to the `people` table.
2. **Registers the conversation reference** so the service can message the person proactively:
   `POST /api/v1/conversation_ref {email, conversation_id}`.
3. **Forwards every message** (freeform — there are no client-side commands) to
   `POST /api/v1/chat {employee_email, text, conversation_id}` and posts the returned
   `reply` markdown verbatim. All intent routing happens service-side; the service uses the
   agentic graph when AWS is available and a deterministic fallback otherwise.
4. **Delivers proactive messages** — a background loop polls
   `GET /api/v1/notifications/pending` every 20s and, for each notification that has a
   `conversation_id`, sends it via the Teams SDK and acks
   `POST /api/v1/notifications/{id}/delivered`. This is how lifecycle nudges
   (`pre_bench_greeting` → `planning_prompt` → `kickoff` → weekly `progress_check`) and the
   `eod_report` reach people.

Those four endpoints are the entire contract between the bot and the service.

## Configuration (`.env` — copy from `.env.example`)

| Var | Purpose |
|---|---|
| `CLIENT_ID` / `CLIENT_SECRET` / `TENANT_ID` | Entra bot registration (provisioned by the M365 Agents Toolkit on F5). |
| `BOT_TYPE` | `UserAssignedMsi` in Azure (uses Managed Identity); empty for local. |
| `BENCH_BACKEND_URL` | The Bench service base URL (default `http://localhost:8000`). |
| `BENCH_API_TOKEN` | Shared bearer token for `/api/v1`. Must match the service's `BENCH_API_TOKEN`. Leave empty when the service runs open (local dev). |

The bot has **no** AWS/Bedrock settings by design.

## Run it

> **Prerequisites:** Python ≥3.12,<3.14, the
> [Microsoft 365 Agents Toolkit VS Code extension](https://aka.ms/teams-toolkit), and a
> [Microsoft 365 dev account](https://docs.microsoft.com/microsoftteams/platform/toolkit/accounts).

1. Start the Bench service first (see `../docs/RUNBOOK.md`):
   `BENCH_ENABLED=1 uv run --group ui --extra agentic uvicorn bench.webapp:app --reload`.
2. In `teams-bot/`: `uv sync`, then fill `.env` (at least `BENCH_BACKEND_URL`, and
   `BENCH_API_TOKEN` if the service sets one).
3. `code .` and press **F5** → *Debug in Teams (Edge)* / *(Chrome)*. Add the app when Teams
   prompts, then message the bot — it forwards to the service and the coach leads the conversation.

For a real pilot the service must be reachable from wherever the bot runs (a dev tunnel for
local F5; App Runner / an internal ALB later). Deploying to Azure App Service uses a
User-Assigned Managed Identity (`BOT_TYPE=UserAssignedMsi`); infra templates are under `infra/`.

## Layout

| Path | Contents |
|---|---|
| `src/app.py` | The thin channel: email resolution, forward-to-`/chat`, proactive poll loop. |
| `src/config.py` | Environment variables (no AWS). |
| `appPackage/` | Teams app manifest + icons (BenchCoach / Endava MVD). |
| `env/`, `infra/`, `m365agents*.yml` | M365 Agents Toolkit project + Azure provisioning. |

## Known issues

- On `Debug in Microsoft 365 Agents Playground` you may see `ECONNREFUSED 127.0.0.1:3978`
  until the Python process is ready — wait for it, then refresh the Playground page.
- After a remote deploy, the first interaction may lag while the service restarts.
