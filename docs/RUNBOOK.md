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

1. Web → *Onboard to bench*: person + Endava Profile PDF + status `pre_bench` + start date.
2. Message the bot once in Teams (registers the conversation reference).
3. ~1 min later the bot proactively sends the pre-bench greeting.
4. Dashboard → set status `active` → kickoff arrives (mandatory courses + suggestions
   matched to the profile + "what's your plan?").
5. Chat your plan/progress — the agent records tasks and check-ins.
6. Dashboard shows verified progress and the proactive contact log; `report` builds the EOD.
