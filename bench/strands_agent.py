"""OPTIONAL — Strands Agents implementation of the Bench Assistant (conversational side).

Same guarded pattern as `agent/strands_agent.py`: the default paths (`bench/app.py` CLI and
`bench/graph.py` daily cycle) run WITHOUT the SDK. Here a Strands agent reasons and decides
when to invoke each bench tool. See ADR 0002 for the Strands/LangGraph split.

Requirements (not needed for the local paths):

    pip install strands-agents bedrock-agentcore
    cp .env.example .env        # AWS_REGION + BEDROCK_MODEL_ID (requires model access)

    python -m bench.strands_agent --employee "Ada Lovelace" --email ada@example.com \\
        --profile backend-dev --track aws-backend-track
"""
from __future__ import annotations

import argparse

from bench.config import BEDROCK_MODEL_ID, BEDROCK_REGION
from bench.prompts import BENCH_SYSTEM_PROMPT
from bench.tools.catalog import load_profile as _load_profile
from bench.tools.catalog import load_track as _load_track
from bench.tools.eod_report import build_eod_report as _build_eod_report
from bench.tools.eod_report import save_eod_report as _save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan as _generate_bench_plan
from bench.tools.state import load_bench_state as _load_bench_state
from bench.tools.state import record_check_in as _record_check_in
from bench.tools.state import start_bench as _start_bench
from bench.tools.state import update_task_status as _update_task_status
from bench.tools.verify_goals import verify_progress as _verify_progress

try:
    from strands import Agent, tool
    from strands.models import BedrockModel
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Strands SDK not installed. This path is optional (Lab 2). "
        "Install with: pip install strands-agents bedrock-agentcore"
    ) from exc


load_profile = tool(_load_profile)
load_track = tool(_load_track)
generate_bench_plan = tool(_generate_bench_plan)
start_bench = tool(_start_bench)
load_bench_state = tool(_load_bench_state)
record_check_in = tool(_record_check_in)
update_task_status = tool(_update_task_status)
verify_progress = tool(_verify_progress)
build_eod_report = tool(_build_eod_report)
save_eod_report = tool(_save_eod_report)

TOOLS = [
    load_profile, load_track, generate_bench_plan, start_bench, load_bench_state,
    record_check_in, update_task_status, verify_progress, build_eod_report, save_eod_report,
]


def build_agent() -> "Agent":
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=BEDROCK_REGION,
    )
    return Agent(model=model, system_prompt=BENCH_SYSTEM_PROMPT, tools=TOOLS)


def main() -> None:
    from bench.config import require_bench_enabled

    require_bench_enabled()
    parser = argparse.ArgumentParser(prog="bench.strands_agent")
    parser.add_argument("--employee", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--track", required=True)
    args = parser.parse_args()

    agent = build_agent()
    agent(
        f"Start bench for {args.employee} ({args.email}) with profile '{args.profile}' and "
        f"track '{args.track}', then present the bench plan and explain today's daily goals."
    )


if __name__ == "__main__":
    main()
