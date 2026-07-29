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
import sys

from bench.config import require_bench_enabled
from bench.seed import seed_if_empty
from bench.tools.catalog import load_profile, load_track
from bench.tools.contracts import (DomainError, execute, onboard_person, require_email,
                                   run_checkin_cycle, save_person_report, update_person_task)
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

    from bench.actor import actor_context

    try:
        with actor_context():
            if args.command == "start":
                state = onboard_person(args.employee, args.email, args.profile, args.track,
                                       starter=start_bench).data
                print(_plan_from_state(state))
            elif args.command == "plan":
                print(_plan_from_state(execute("load_person", load_bench_state,
                                               require_email(args.email)).data))
            elif args.command == "tasks":
                state = execute("load_person", load_bench_state, require_email(args.email)).data
                for task in state["tasks"]:
                    due = f" due {task['due_date']}" if task["due_date"] else ""
                    print(f"#{task['task_id']} [{task['status']}] {task['title']} "
                          f"({task['category']}, {task['follow_up']}{due})")
            elif args.command == "task":
                print(json.dumps(update_person_task(args.email, args.id, args.status,
                                         args.evidence, args.note).data,
                                 indent=2, ensure_ascii=False))
            elif args.command == "checkin":
                print(json.dumps(run_checkin_cycle(args.email, args.period, planned=args.planned,
                                         blockers=args.blockers,
                                         task_updates=[]).data,
                                 indent=2, ensure_ascii=False))
            elif args.command == "verify":
                state = execute("load_person", load_bench_state, require_email(args.email)).data
                track = load_track(state["track_id"])
                print(json.dumps(verify_progress(state, track, args.date), indent=2, ensure_ascii=False))
            elif args.command == "report":
                result = save_person_report(args.email, args.date).data
                print(result["report"])
                print(f"\n[saved to {result['path']}]")
    except DomainError as exc:
        print(exc.safe_message, file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
