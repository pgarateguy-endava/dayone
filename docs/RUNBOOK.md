# Runbook — run & test the Bench project

## Tests (no AWS, no Teams needed)

```bash
uv run --group ui pytest
```

## Service (backend + web UI + API + proactive scheduler)

```bash
aws sso login --profile <your-sso-profile>        # only if the token expired
uv sync --group ui --extra agentic                # first time / after pull
uv run --group ui --extra agentic uvicorn bench.webapp:app --reload
# open http://localhost:8000
```

Config comes from the repo-root `.env` (gitignored): `BENCH_ENABLED=1`, `BENCH_USE_LLM=1`,
`AWS_PROFILE`, `AWS_REGION`, `BEDROCK_MODEL_ID`. Without `--extra agentic` the service still
runs; chat falls back to deterministic mode.

If the DB schema changed after a pull: `rm .local-progress/bench.db` (re-seeds itself).

## Verify the AWS connections (from local)

All AWS use is from local via the SSO profile; each service has a local fallback, so this
is optional and never required for the demo. Region is `us-west-2`.

```bash
# 0) SSO login (tokens expire — do this first, and before any demo)
aws sso login --profile pedro.garateguy.endava
aws sts get-caller-identity --profile pedro.garateguy.endava

# 1) Bedrock — if the agent replies, it's connected
uv run --group ui --extra agentic python -m bench.agent_graph \
  --email you@endava.com --ask "hola"

# 2) S3 — create the bucket once (the app writes but does not create it),
#    then set BENCH_DOCS_S3_BUCKET in .env and restart the service
aws s3 mb s3://bench-docs-mvp --region us-west-2 --profile pedro.garateguy.endava
#   after an onboard-with-PDF or an EOD report:
aws s3 ls s3://bench-docs-mvp --recursive --profile pedro.garateguy.endava

# 3) DynamoDB — tables auto-create on first use; set BENCH_STORAGE=dynamodb in .env,
#    restart, message the bot + change a bench date, then:
aws dynamodb list-tables --region us-west-2 --profile pedro.garateguy.endava
aws dynamodb scan --table-name bench-notifications --region us-west-2 --profile pedro.garateguy.endava
```

`.env` AWS flags (all optional; unset = local fallback):
`BENCH_DOCS_S3_BUCKET` (S3 for reports/PDFs), `BENCH_STORAGE=dynamodb` (per-person
notification state on DynamoDB), `BENCH_DYNAMODB_PREFIX` (table name prefix, default `bench`).

## Probe the agent without Teams

```bash
uv run --group ui --extra agentic python -m bench.agent_graph \
  --email you@endava.com --ask "hola, qué me recomendás estudiar?"

curl -s -X POST http://localhost:8000/api/v1/chat -H "Content-Type: application/json" \
  -d '{"employee_email":"you@endava.com","text":"hola"}'
```

## Teams bot (thin channel)

```bash
cd teams-bot
uv sync                       # first time
# .env needs: PORT, CLIENT_ID, CLIENT_SECRET, TENANT_ID, BENCH_BACKEND_URL
code .                        # F5 -> "Debug in Teams (Edge)"
```

## Demo flow

1. Web → *Onboard to bench*: person + Endava Profile PDF + `pre_bench` start date.
2. Message the bot once in Teams (registers the conversation reference).
3. ~1 min later the bot proactively suggests updating the Endava Profile first.
4. Reply that the Profile is ready; the agent marks the profile-update task as done.
5. One day before bench, the bot asks whether to start planning the bench period.
6. Planning starts with Mandatory courses, then certifications/courses matched to the Profile.
7. Dashboard → set status `active` → kickoff arrives; chat your plan/progress.
8. Dashboard shows verified progress and the proactive contact log; `report` builds the EOD.
