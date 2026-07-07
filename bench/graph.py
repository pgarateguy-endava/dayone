"""Daily-cycle workflow as a LangGraph state machine (see ADR 0002).

Fixed pipeline (this is deliberately NOT an agent — the order must be guaranteed):

    load_context -> record_check_in -> verify_goals -> [pm only] summarize -> report -> notify

- Runs fully offline: every node is deterministic.
- The `summarize` node optionally uses Bedrock (env BENCH_USE_LLM=1 + boto3 + model access);
  on any failure it falls back to a deterministic summary. The LLM only rephrases the
  verification result; it never decides goal completion.
- Production: deployed on AgentCore Runtime, triggered twice a day by EventBridge;
  `notify` posts to Teams instead of writing a file.

Requires: pip install langgraph

Usage:

    python -m bench.graph --email ada@example.com --period pm \\
        --done "1:course at 45%" --blockers ""
"""
from __future__ import annotations

import argparse
import os
from typing import Any, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except ImportError as exc:  # pragma: no cover
    raise SystemExit("LangGraph is required for the daily cycle: pip install langgraph") from exc

from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.load_track import load_track
from bench.tools.state import load_bench_state, record_check_in
from bench.tools.verify_goals import verify_daily_goals


class CycleState(TypedDict, total=False):
    # inputs
    employee_email: str
    period: str                # "am" | "pm"
    done_goals: list[dict]     # [{"goal": int, "evidence": str}]
    planned: list[str]
    blockers: str
    # accumulated by nodes
    bench_state: dict
    track: dict
    verification: dict
    summary: str
    report_md: str
    report_path: str
    notified: list[str]


def load_context(state: CycleState) -> dict[str, Any]:
    bench_state = load_bench_state(state["employee_email"])
    track = load_track(bench_state["track_id"])
    return {"bench_state": bench_state, "track": track}


def check_in(state: CycleState) -> dict[str, Any]:
    record_check_in(
        state["employee_email"],
        state["period"],
        done_goals=state.get("done_goals", []),
        planned=state.get("planned", []),
        blockers=state.get("blockers", ""),
    )
    # re-load so verification sees the event just recorded
    return {"bench_state": load_bench_state(state["employee_email"])}


def verify(state: CycleState) -> dict[str, Any]:
    return {"verification": verify_daily_goals(state["bench_state"], state["track"])}


def _deterministic_summary(verification: dict) -> str:
    risky = [d for d in verification["deadlines"] if d["level"] != "ok"]
    parts = [
        f"{verification['goals_met']}/{verification['goals_total']} daily goals met "
        f"({int(verification['completion_rate'] * 100)}%)."
    ]
    if verification["blockers"]:
        parts.append(f"Blockers reported: {len(verification['blockers'])}.")
    if risky:
        parts.append("Deadlines needing attention: "
                     + "; ".join(f"{d['description']} ({d['level']}, {d['days_left']:+d}d)" for d in risky))
    return " ".join(parts)


def summarize(state: CycleState) -> dict[str, Any]:
    """LLM-optional narrative summary. Deterministic fallback always available."""
    verification = state["verification"]
    if os.environ.get("BENCH_USE_LLM") == "1":
        try:  # optional Bedrock enhancement — requires AWS credentials + model access
            import boto3

            client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            response = client.converse(
                modelId=os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
                messages=[{"role": "user", "content": [{"text":
                    "Write a 2-3 sentence status summary for a People Lead based only on this "
                    f"verification data (do not add facts): {verification}"}]}],
            )
            return {"summary": response["output"]["message"]["content"][0]["text"]}
        except Exception:
            pass
    return {"summary": _deterministic_summary(verification)}


def report(state: CycleState) -> dict[str, Any]:
    report_md = build_eod_report(state["bench_state"], state["track"],
                                 state["verification"], summary=state.get("summary", ""))
    path = save_eod_report(report_md, state["employee_email"], state["verification"]["date"])
    return {"report_md": report_md, "report_path": path}


def notify(state: CycleState) -> dict[str, Any]:
    """Simulated Teams delivery: in production, post to a Teams webhook/Graph API here."""
    recipients = [r["email"] for r in state["track"].get("responsibles", [])]
    print(f"[notify] EOD report for {state['employee_email']} -> {recipients}")
    print(f"[notify] (simulated Teams message; file: {state['report_path']})")
    return {"notified": recipients}


def _route_after_verify(state: CycleState) -> str:
    """AM run: stop after verification (goals for the day are set). PM run: full report."""
    return "summarize" if state["period"] == "pm" else END


def build_graph():
    graph = StateGraph(CycleState)
    graph.add_node("load_context", load_context)
    graph.add_node("check_in", check_in)
    graph.add_node("verify", verify)
    graph.add_node("summarize", summarize)
    graph.add_node("report", report)
    graph.add_node("notify", notify)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "check_in")
    graph.add_edge("check_in", "verify")
    graph.add_conditional_edges("verify", _route_after_verify, {"summarize": "summarize", END: END})
    graph.add_edge("summarize", "report")
    graph.add_edge("report", "notify")
    graph.add_edge("notify", END)
    return graph.compile()


def _parse_done(values: list[str]) -> list[dict]:
    done = []
    for value in values:
        goal, _, evidence = value.partition(":")
        done.append({"goal": int(goal), "evidence": evidence.strip()})
    return done


def main() -> None:
    parser = argparse.ArgumentParser(prog="bench.graph", description="Bench daily cycle (LangGraph)")
    parser.add_argument("--email", required=True)
    parser.add_argument("--period", required=True, choices=["am", "pm"])
    parser.add_argument("--planned", action="append", default=[])
    parser.add_argument("--done", action="append", default=[])
    parser.add_argument("--blockers", default="")
    args = parser.parse_args()

    app = build_graph()
    result = app.invoke({
        "employee_email": args.email,
        "period": args.period,
        "planned": args.planned,
        "done_goals": _parse_done(args.done),
        "blockers": args.blockers,
    })

    if args.period == "pm":
        print(result["report_md"])
    else:
        verification = result["verification"]
        print(f"AM check-in recorded for {args.email}.")
        print(f"Today's goals ({verification['goals_total']}):")
        for i, goal in enumerate(result["track"].get("daily_goals", []), start=1):
            print(f"  {i}. {goal}")


if __name__ == "__main__":
    main()
