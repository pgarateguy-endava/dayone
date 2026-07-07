# ADR 0001: Bench as a parallel domain on a feature branch

- **Status:** accepted
- **Date:** 2026-07-07

## Context

The repo is workshop material for an onboarding assistant (Strands + AgentCore). We want a
real internal application: an assistant for people on Endava's Bench. Both share the same
architecture: declarative YAML + explicit Python tools + deterministic generation + optional
agent orchestration.

## Decision

Build Bench as a **parallel domain** in the `feature/bench` branch:

- New `bench/` package and `tracks/` data dir; `main` and the onboarding labs stay untouched.
- `profiles/*.yaml` are **shared**: they remain the single source of truth for role-based
  permissions (Bench never redefines access).
- Bench follows the same tool contract (read / generation / write / dangerous) from
  `AGENTCORE_STRANDS_NOTES.md` and the same golden rule: everything must run locally without
  the SDK (Lab 1 parity).

## Consequences

- The workshop material remains valid; Bench can be demoed from the branch and merged later
  if the team adopts it.
- Some duplication (two app entry points) accepted for teaching clarity.
- Profile schema changes must consider both domains.
