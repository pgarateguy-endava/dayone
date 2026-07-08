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

## Update (2026-07, current LangGraph docs)

Verified against docs.langchain.com (langgraph 1.x, docs moved off langchain-ai.github.io):

- Our 0.2-style graph API (`StateGraph`, `START`/`END`, `add_conditional_edges`) is unchanged
  in langgraph 1.x — `bench/graph.py` needs no migration.
- The current way to **associate the model with tools** inside a graph is
  `model.bind_tools(tools)` + `ToolNode` + `tools_condition` (`langgraph.prebuilt`, not
  deprecated). Implemented in `bench/agent_graph.py`.
- `create_react_agent` is deprecated in favor of `create_agent` from **langchain 1.x**
  (`from langchain.agents import create_agent`, `prompt=` renamed to `system_prompt=`).
- Bedrock models plug in via `langchain-aws`'s `ChatBedrockConverse`, which supports
  `bind_tools`.

This gives the Bench domain three orchestration flavors on one case, all deployable to
AgentCore Runtime: deterministic pipeline (`graph.py`), agentic loop where the LLM decides
per progress (`agent_graph.py`), and Strands agent (`strands_agent.py`).

## Consequences

- Team learns both dominant patterns (agent-with-tools vs. state-machine workflow) on one case.
- One extra dependency (`langgraph`) — local-only, no AWS required.
- Clear seam: anything requiring guaranteed execution order goes in the graph; anything
  exploratory goes in the agent.
