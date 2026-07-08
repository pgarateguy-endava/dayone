"""OPTIONAL — agentic LangGraph: the LLM is bound to the bench tools and decides which to call.

This complements `bench/graph.py` (deterministic pipeline) with the OTHER LangGraph pattern,
per the current docs (langgraph 1.x, docs.langchain.com):

- `model.bind_tools(tools)` associates the model with the tools;
- `ToolNode` (langgraph.prebuilt) executes whatever tool calls the model emits;
- `tools_condition` routes: if the last AI message contains tool calls -> ToolNode, else END;
- fully prebuilt alternative: `create_agent` from langchain 1.x (successor of the
  deprecated `create_react_agent`).

Division of labor (ADR 0002): the AI decides *what to look at and what to say* according to
progress; goal completion is still computed by `verify_daily_goals` (deterministic tool).

Requirements (not needed for the local paths):

    uv sync --group ui --extra agentic     # langchain + langchain-aws
    # AWS credentials + Bedrock model access (see docs/BENCH_AWS_ACCESS_CHECKLIST.md)

    BENCH_ENABLED=1 uv run python -m bench.agent_graph --email ada@example.com \\
        --ask "How am I doing today? What should I focus on next?"
"""
from __future__ import annotations

import argparse
import os

try:
    from langchain_aws import ChatBedrockConverse
    from langchain_core.messages import SystemMessage
    from langchain_core.tools import tool
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode, tools_condition
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The agentic graph needs langchain + langchain-aws: uv sync --extra agentic"
    ) from exc

from bench.config import require_bench_enabled
from bench.prompts import BENCH_SYSTEM_PROMPT
from bench.tools.catalog import load_track as _load_track
from bench.tools.state import load_bench_state as _load_bench_state
from bench.tools.verify_goals import verify_progress as _verify_progress


@tool
def get_bench_status(employee_email: str) -> dict:
    """Get today's verified progress for a person on bench: task statuses and follow-ups
    (decided deterministically from the database, never by the model), blockers and
    deadline risks."""
    state = _load_bench_state(employee_email)
    track = _load_track(state["track_id"])
    return _verify_progress(state, track)


@tool
def get_bench_track(track_id: str) -> dict:
    """Get the declarative bench track: mandatory courses, certification options,
    daily goals, profile tasks and deadlines. Source of truth — do not invent items."""
    return _load_track(track_id)


@tool
def get_bench_state(employee_email: str) -> dict:
    """Get the raw bench record for a person: profile, track and check-in history."""
    return _load_bench_state(employee_email)


TOOLS = [get_bench_status, get_bench_track, get_bench_state]


def build_agent_graph():
    """Classic agentic loop: llm_call <-> ToolNode until the model stops calling tools."""
    model = ChatBedrockConverse(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    model_with_tools = model.bind_tools(TOOLS)

    def llm_call(state: MessagesState):
        return {"messages": [model_with_tools.invoke(
            [SystemMessage(content=BENCH_SYSTEM_PROMPT)] + state["messages"]
        )]}

    builder = StateGraph(MessagesState)
    builder.add_node("llm_call", llm_call)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", tools_condition)  # tool_calls -> "tools", else END
    builder.add_edge("tools", "llm_call")
    return builder.compile()


def main() -> None:
    require_bench_enabled()
    parser = argparse.ArgumentParser(prog="bench.agent_graph")
    parser.add_argument("--email", required=True)
    parser.add_argument("--ask", required=True, help="Question for the bench assistant")
    args = parser.parse_args()

    graph = build_agent_graph()
    result = graph.invoke({"messages": [
        {"role": "user", "content": f"(employee: {args.email}) {args.ask}"}
    ]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
