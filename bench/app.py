"""Bench Assistant - local CLI over the SQLite catalog (no SDK, no AWS).

Usage examples:

    python -m bench.seed                     # load dummy catalog data (first time)
    python -m bench.app start --employee "Ada Lovelace" --email ada@example.com \\
        --profile backend-dev --track aws-backend-track
    python -m bench.app plan --email ada@example.com
    python -m bench.app tasks --email ada@example.com
    python -m bench.app task --email ada@example.com --id 3 --status in_progress \\
        --evidence "course at 45%"
    python -m bench.app checkin --email ada@example.com --period am --planned "Course module 3"
    python -m bench.app verify --email ada@example.com
    python -m bench.app report --email ada@example.com
"""
from __future__ import annotations

import argparse
import json

from bench.config import require_bench_enabled
from bench.seed import seed_if_empty
from bench.tools.catalog import load_profile, load_track
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.state import (
    load_bench_state,
    record_check_in,
    start_bench,
    update_task_status,
)
from bench.tools.verify_goals import verify_progress


def _plan_from_state(state: dict) -> str:
    profile = load_profile(state["profile_id"])
    track = load_track(state["track_id"])
    return generate_bench_plan(state["employee_name"], state["employee_email"], profile, track)


def main() -> None:
    require_bench_enabled()
    seed_if_empty()
    parser = argparse.ArgumentParser(prog="bench.app", description="Bench Assistant (local MVP)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Assign a person to bench with a track")
    p_start.add_argument("--employee", required=True)
    p_start.add_argument("--email", required=True)
    p_start.add_argument("--profile", required=True)
    p_start.add_argument("--track", required=True)

    for name, help_text in (("plan", "Print the bench plan"),
                            ("tasks", "List the person's tasks with status"),
                            ("verify", "Verify today's progress (deterministic)"),
                            ("report", "Build and save the EOD report")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--email", required=True)
        if name in ("verify", "report"):
            p.add_argument("--date", default=None)

    p_task = sub.add_parser("task", help="Update a task's status/evidence")
    p_task.add_argument("--email", required=True)
    p_task.add_argument("--id", type=int, required=True)
    p_task.add_argument("--status", required=True,
                        choices=["pending", "in_progress", "done", "blocked"])
    p_task.add_argument("--evidence", default="")
    p_task.add_argument("--note", default="")

    p_check = sub.add_parser("checkin", help="Record an AM/PM check-in")
    p_check.add_argument("--email", required=True)
    p_check.add_argument("--period", required=True, choices=["am", "pm"])
    p_check.add_argument("--planned", action="append", default=[])
    p_check.add_argument("--blockers", default="")
    p_check.add_argument("--note", default="")

    args = parser.parse_args()

    if args.command == "start":
        state = start_bench(args.employee, args.email, args.profile, args.track)
        print(_plan_from_state(state))
    elif args.command == "plan":
        print(_plan_from_state(load_bench_state(args.email)))
    elif args.command == "tasks":
        state = load_bench_state(args.email)
        for task in state["tasks"]:
            due = f" due {task['due_date']}" if task["due_date"] else ""
            print(f"#{task['task_id']} [{task['status']}] {task['title']} "
                  f"({task['category']}, {task['follow_up']}{due})")
    elif args.command == "task":
        print(json.dumps(update_task_status(args.email, args.id, args.status,
                                            args.evidence, args.note),
                         indent=2, ensure_ascii=False))
    elif args.command == "checkin":
        print(json.dumps(record_check_in(args.email, args.period, planned=args.planned,
                                         blockers=args.blockers, note=args.note),
                         indent=2, ensure_ascii=False))
    elif args.command == "verify":
        state = load_bench_state(args.email)
        track = load_track(state["track_id"])
        print(json.dumps(verify_progress(state, track, args.date), indent=2, ensure_ascii=False))
    elif args.command == "report":
        state = load_bench_state(args.email)
        track = load_track(state["track_id"])
        verification = verify_progress(state, track, args.date)
        report = build_eod_report(state, track, verification)
        path = save_eod_report(report, args.email, verification["date"])
        print(report)
        print(f"\n[saved to {path}]")


if __name__ == "__main__":
    main()
