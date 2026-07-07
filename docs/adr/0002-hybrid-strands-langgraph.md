# ADR 0002: Hybrid engine — Strands for conversation, LangGraph for the daily cycle

- **Status:** accepted
- **Date:** 2026-07-07

## Context

The Bench domain has two very different workloads:

1. **Conversational**: a person asks for their plan, marks steps, asks questions. Open-ended;
   the LLM decides which tool to call. This is what Strands Agents models well and what the
   workshop teaches.
2. **Scheduled pipeline**: twice-daily check-ins → goal verification → EOD report → notify
   responsibles. Fixed order, explicit state, must run even with a degraded/absent LLM.
   Letting an agent improvise this flow adds risk with no benefit.

AgentCore Runtime is framework-agnostic: it hosts Strands, LangGraph, or plain Python equally.

## Decision

- `bench/strands_agent.py`: Strands agent exposing the bench tools (same guarded-import
  pattern as `agent/strands_agent.py`).
- `bench/graph.py`: LangGraph `StateGraph` for the daily cycle. Nodes are deterministic;
  the LLM is an **optional enhancement** in the report-summary node only (env-gated), so the
  graph runs end-to-end offline.
- Production: both deployed on AgentCore Runtime; EventBridge triggers the graph at the two
  daily check-in times.

## Consequences

- Team learns both dominant patterns (agent-with-tools vs. state-machine workflow) on one case.
- One extra dependency (`langgraph`) — local-only, no AWS required.
- Clear seam: anything requiring guaranteed execution order goes in the graph; anything
  exploratory goes in the agent.
