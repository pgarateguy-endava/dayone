"""Bench Assistant - local CLI (Lab 1 parity: no SDK, no AWS).

Usage examples:

    python -m bench.app start --employee "Ada Lovelace" --email ada@example.com \\
        --profile backend-dev --track aws-backend-track
    python -m bench.app plan --email ada@example.com
    python -m bench.app checkin --email ada@example.com --period am --planned "Course module 3"
    python -m bench.app checkin --email ada@example.com --period pm \\
        --done "1:course at 45%" --done "2:https://github.com/me/repo/commit/abc" --blockers ""
    python -m bench.app verify --email ada@example.com
    python -m bench.app report --email ada@example.com
"""
from __future__ import annotations

import argparse
import json

from agent.tools.load_profile import load_profile
from bench.config import require_bench_enabled
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.load_track import load_track
from bench.tools.state import load_bench_state, record_check_in, start_bench
from bench.tools.verify_goals import verify_daily_goals


def _plan_from_state(state: dict) -> str:
    profile = load_profile(state["profile_id"])
    track = load_track(state["track_id"])
    return generate_bench_plan(state["employee_name"], state["employee_email"], profile, track)


def _parse_done(values: list[str]) -> list[dict]:
    """Parse repeated --done 'N[:evidence]' flags into goal/evidence dicts."""
    done = []
    for value in values:
        goal, _, evidence = value.partition(":")
        done.append({"goal": int(goal), "evidence": evidence.strip()})
    return done


def main() -> None:
    require_bench_enabled()
    parser = argparse.ArgumentParser(prog="bench.app", description="Bench Assistant (local MVP)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Assign a person to bench with a track")
    p_start.add_argument("--employee", required=True)
    p_start.add_argument("--email", required=True)
    p_start.add_argument("--profile", required=True)
    p_start.add_argument("--track", required=True)

    p_plan = sub.add_parser("plan", help="Print the bench plan")
    p_plan.add_argument("--email", required=True)

    p_check = sub.add_parser("checkin", help="Record an AM/PM check-in")
    p_check.add_argument("--email", required=True)
    p_check.add_argument("--period", required=True, choices=["am", "pm"])
    p_check.add_argument("--planned", action="append", default=[], help="AM: what you'll work on")
    p_check.add_argument("--done", action="append", default=[],
                         help="PM: goal number with optional evidence, e.g. '1:course at 45%%'")
    p_check.add_argument("--blockers", default="")
    p_check.add_argument("--note", default="")

    p_verify = sub.add_parser("verify", help="Verify today's goals (deterministic)")
    p_verify.add_argument("--email", required=True)
    p_verify.add_argument("--date", default=None)

    p_report = sub.add_parser("report", help="Build and save the EOD report")
    p_report.add_argument("--email", required=True)
    p_report.add_argument("--date", default=None)

    args = parser.parse_args()

    if args.command == "start":
        state = start_bench(args.employee, args.email, args.profile, args.track)
        print(_plan_from_state(state))
    elif args.command == "plan":
        print(_plan_from_state(load_bench_state(args.email)))
    elif args.command == "checkin":
        event = record_check_in(
            args.email, args.period, done_goals=_parse_done(args.done),
            planned=args.planned, blockers=args.blockers, note=args.note,
        )
        print(json.dumps(event, indent=2, ensure_ascii=False))
    elif args.command == "verify":
        state = load_bench_state(args.email)
        track = load_track(state["track_id"])
        print(json.dumps(verify_daily_goals(state, track, args.date), indent=2, ensure_ascii=False))
    elif args.command == "report":
        state = load_bench_state(args.email)
        track = load_track(state["track_id"])
        verification = verify_daily_goals(state, track, args.date)
        report = build_eod_report(state, track, verification)
        path = save_eod_report(report, args.email, verification["date"])
        print(report)
        print(f"\n[saved to {path}]")


if __name__ == "__main__":
    main()
