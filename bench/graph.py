"""Daily-cycle workflow as a LangGraph state machine (see ADR 0002).

Fixed pipeline (this is deliberately NOT an agent — the order must be guaranteed):

    load_context -> check_in -> verify -> [pm only] summarize -> report -> notify

- Runs fully offline: every node is deterministic.
- The `summarize` node optionally uses Bedrock (env BENCH_USE_LLM=1 + boto3 + model access);
  on any failure it falls back to a deterministic summary. The LLM only rephrases the
  verification result; it never decides task status.
- Production: deployed on AgentCore Runtime, triggered twice a day by EventBridge;
  `notify` posts to Teams instead of writing a file.

Usage:

    python -m bench.graph --email ada@example.com --period pm \\
        --task "3=in_progress:course at 45%" --blockers ""
"""
from __future__ import annotations

import argparse
import os
from typing import Any, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except ImportError as exc:  # pragma: no cover
    raise SystemExit("LangGraph is required for the daily cycle: pip install langgraph") from exc

from bench.config import BEDROCK_MODEL_ID, BEDROCK_REGION, require_bench_enabled
from bench.tools.catalog import load_track
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.state import load_bench_state, record_check_in, update_task_status
from bench.tools.verify_goals import verify_progress


class CycleState(TypedDict, total=False):
    # inputs
    employee_email: str
    period: str                 # "am" | "pm"
    task_updates: list[dict]    # [{"task_id": int, "status": str, "evidence": str, "note": str}]
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
    notified_teams: list[str]


def load_context(state: CycleState) -> dict[str, Any]:
    bench_state = load_bench_state(state["employee_email"])
    track = load_track(bench_state["track_id"])
    return {"bench_state": bench_state, "track": track}


def check_in(state: CycleState) -> dict[str, Any]:
    for update in state.get("task_updates", []):
        update_task_status(
            state["employee_email"], int(update["task_id"]), update["status"],
            evidence=update.get("evidence", ""), note=update.get("note", ""))
    record_check_in(
        state["employee_email"], state["period"],
        planned=state.get("planned", []), blockers=state.get("blockers", ""))
    # re-load so verification sees what was just recorded
    return {"bench_state": load_bench_state(state["employee_email"])}


def verify(state: CycleState) -> dict[str, Any]:
    return {"verification": verify_progress(state["bench_state"], state["track"])}


def _deterministic_summary(verification: dict) -> str:
    risky = [d for d in verification["deadlines"] if d["level"] in ("overdue", "at_risk")]
    parts = [
        f"{verification['tasks_done']}/{verification['tasks_total']} tasks done overall; "
        f"today {verification['touched_today']} of "
        f"{verification['touched_today'] + verification['pending_today']} follow-ups touched."
    ]
    if verification["blockers"]:
        parts.append(f"Blockers reported: {len(verification['blockers'])}.")
    if risky:
        parts.append("Deadlines needing attention: "
                     + "; ".join(f"{d['title']} ({d['level']}, {d['days_left']:+d}d)" for d in risky))
    return " ".join(parts)


def summarize(state: CycleState) -> dict[str, Any]:
    """LLM-optional narrative summary. Deterministic fallback always available."""
    verification = state["verification"]
    if os.environ.get("BENCH_USE_LLM") == "1":
        try:  # optional Bedrock enhancement — requires AWS credentials + model access
            import boto3

            client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
            response = client.converse(
                modelId=BEDROCK_MODEL_ID,
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
    """Deliver the EOD report to the track's responsibles (ADR 0004).

    The durable record is always the saved file. Additionally, for each responsible who
    has talked to the bot (has a conversation ref), queue a Teams proactive message; the
    bot's poll loop delivers it. Responsibles without a ref fall back to file + dashboard.
    """
    from bench.notify import queue_notification

    recipients = [r["email"] for r in state["track"].get("responsibles", [])]
    queued = [email for email in recipients
              if queue_notification(email, "eod_report", state["report_md"])]
    print(f"[notify] EOD report for {state['employee_email']} -> {recipients} "
          f"(queued to Teams: {queued or 'none'}; file: {state['report_path']})")
    return {"notified": recipients, "notified_teams": queued}


def _route_after_verify(state: CycleState) -> str:
    """AM run: stop after verification (the day is planned). PM run: full report."""
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


def parse_task_updates(values: list[str]) -> list[dict]:
    """Parse repeated --task 'ID=STATUS[:evidence]' flags."""
    updates = []
    for value in values:
        task_id, _, rest = value.partition("=")
        status, _, evidence = rest.partition(":")
        updates.append({"task_id": int(task_id), "status": status.strip(),
                        "evidence": evidence.strip()})
    return updates


def main() -> None:
    require_bench_enabled()
    parser = argparse.ArgumentParser(prog="bench.graph", description="Bench daily cycle (LangGraph)")
    parser.add_argument("--email", required=True)
    parser.add_argument("--period", required=True, choices=["am", "pm"])
    parser.add_argument("--planned", action="append", default=[])
    parser.add_argument("--task", action="append", default=[],
                        help="Task update 'ID=STATUS[:evidence]', e.g. '3=done:course 100%%'")
    parser.add_argument("--blockers", default="")
    args = parser.parse_args()

    from bench.actor import actor_context

    with actor_context():
        app = build_graph()
        result = app.invoke({
            "employee_email": args.email,
            "period": args.period,
            "planned": args.planned,
            "task_updates": parse_task_updates(args.task),
            "blockers": args.blockers,
        })

    if args.period == "pm":
        print(result["report_md"])
    else:
        verification = result["verification"]
        print(f"AM check-in recorded for {args.email}.")
        print(f"Tasks to follow up today ({len(verification['follow_up_today'])}):")
        for item in verification["follow_up_today"]:
            print(f"  #{item['task_id']} [{item['status']}] {item['title']}")


if __name__ == "__main__":
    main()
