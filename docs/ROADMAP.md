# Bench Assistant — Roadmap

Status: `feature/bench` merged with the pilot-hardening PR (#1). 32 tests green.
Demo target: **Wednesday**, running **locally** (service on localhost + bot via dev tunnel).

## Milestone 0 — Demo-ready (Mon–Tue, ~8h)

Everything here is demo-critical and needs **no** AWS deployment (only a live Bedrock SSO
session for the chat).

1. **UI polish** (complementary but most visible). Restyle already landed; remaining:
   consistent spacing, a proper header/logo, empty states, and make the dashboard the
   clear "hero" screen. ~3h.
2. **Make every flow editable + tested end-to-end.** Audit each screen: onboard, roles,
   tracks, tasks, knowledge, status/date. Confirm the date-change → proactive-message flow
   works (the bug you hit was fixed by the hardening PR — verify it live). ~2h.
3. **Responsibles from the UI** — add/assign responsibles per track and confirm the EOD
   report reaches them (file + Teams proactive). Rehearse "answer a responsible". ~1h.
4. **Demo script rehearsal** — run the full narrative twice, `aws sso login` first. ~1h.

### Stretch (Tue, only if 1–4 are done): DynamoDB behind a storage flag
Migrate `bench/tools/state.py` + `db.py` reads/writes behind `BENCH_STORAGE=sqlite|dynamodb`.
Guardrail: **default stays `sqlite`**, so a DynamoDB problem can never break Wednesday.
Needs AWS access resolved first. If not resolved by Tue noon, skip — it adds risk with zero
visible value in a local demo.

## Milestone 1 — Pilot (1–2 weeks, after AWS access)

- **Unblock AWS access** (critical path, gestión not code): Bedrock model access for the team
  incl. Ignacio's account ("no subscription"); see `docs/BENCH_AWS_ACCESS_CHECKLIST.md`.
- **Host the service** where the bot can reach it (App Runner / EC2 + ALB), so it's not your
  localhost. Set `BENCH_API_TOKEN` (auth already built).
- **Publish the Teams bot** in the Endava tenant — needs a Teams admin to approve/upload the
  app package; a personal account can't publish org-wide.
- Run with 3–5 real bench people; collect feedback.

## Milestone 2 — Real data (2–3 weeks)

- **DynamoDB** as the production store (finish the storage-backend flag from M0 stretch).
- **RAG over profile PDFs** (journey B3): Bedrock Knowledge Base + S3, so the agent gives
  grounded, cited answers instead of today's deterministic tag matching. This is the natural
  home for the profile-PDF suggestions.
- Load Endava's **real** course/cert catalog into the knowledge base and connect real profiles.

## Milestone 3 — Scale & integrations (1+ month)

- **EventBridge** for the schedulers (today: in-process loops).
- **AgentCore Runtime** for the agent; **CloudWatch/X-Ray** observability; **Guardrails**.
- **Repo feedback bot** (journey B4, CodeRabbit-style), specified but not built.

## Carryover from the original repo (workshop Labs)

- **Lab 1** (local, no SDK): ✅ done and preserved (CI `onboarding` job enforces it).
- **Lab 2** (Strands + Bedrock real agent): code ready (`bench/strands_agent.py`), blocked on
  AWS access. → Milestone 1.
- **Lab 3** (AWS accelerator `sample-strands-agentcore-starter`: CDK, Cognito, KB, Memory,
  Runtime): not started. → Milestone 2/3. This is the biggest carryover item.
- Original onboarding domain (`agent/`, YAML profiles/projects) untouched on `main`.

## The critical path

Everything past the Wednesday demo depends on **AWS access being provisioned by Endava**.
Decide in the call who owns chasing it — it is the single blocker for Milestones 1–3.
