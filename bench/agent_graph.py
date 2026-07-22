"""Conversational bench agent — the LLM leads, bound to bench tools (ADR 0002/0004).

Pattern per current LangGraph docs (1.x): `model.bind_tools` + `ToolNode` +
`tools_condition`, plus a **checkpointer** so each Teams conversation keeps memory
(`thread_id` = conversation id).

Safety model:
- The employee identity is bound SERVER-SIDE: tools are created per-request closed over
  the authenticated email. The LLM cannot act on anyone else's data.
- Goal completion, verification and the EOD report remain deterministic tools;
  the model records what the person reports and narrates — it never computes progress.

Requirements (not needed for the deterministic paths):

    uv sync --extra agentic          # langchain + langchain-aws (+ sqlite checkpointer)
    export AWS_PROFILE=... AWS_REGION=us-west-2 BEDROCK_MODEL_ID=...

    BENCH_ENABLED=1 uv run python -m bench.agent_graph --email ada@example.com \\
        --ask "termine el modulo 3 del curso, y estoy trabado con la licencia de udemy"
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
        "The conversational agent needs langchain + langchain-aws: uv sync --extra agentic"
    ) from exc

try:  # persistent conversation memory if available, in-memory otherwise
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
    import sqlite3 as _sqlite3

    from bench.config import PROGRESS_DIR

    PROGRESS_DIR.mkdir(exist_ok=True)
    _CHECKPOINTER = SqliteSaver(
        _sqlite3.connect(PROGRESS_DIR / "chat-memory.db", check_same_thread=False))
except Exception:  # pragma: no cover
    from langgraph.checkpoint.memory import InMemorySaver

    _CHECKPOINTER = InMemorySaver()

from bench.config import BEDROCK_MODEL_ID, BEDROCK_REGION, require_bench_enabled
from bench.prompts import BENCH_SYSTEM_PROMPT
from bench.tools import catalog as _catalog
from bench.tools.eod_report import build_eod_report as _build_eod_report
from bench.tools.eod_report import save_eod_report as _save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan as _generate_bench_plan
from bench.tools.state import load_bench_state as _load_bench_state
from bench.tools.state import mark_profile_update_done as _mark_profile_update_done
from bench.tools.state import mark_task_done_by_title as _mark_task_done_by_title
from bench.tools.state import record_check_in as _record_check_in
from bench.tools.state import start_bench as _start_bench
from bench.tools.state import update_task_status as _update_task_status
from bench.tools.verify_goals import verify_progress as _verify_progress

COACH_PROMPT = BENCH_SYSTEM_PROMPT + """

You are chatting on Teams with ONE person on bench (their identity is already resolved;
your tools operate only on their data). Lead the conversation like a coach:

- If they are not on bench yet, offer to set them up: show the catalog, ask for role and
  track, then start their bench and present the plan.
- When they tell you what they did, record it: update the matching task's status with
  their words as evidence/note, and register a check-in (pm if they report completions,
  am if they are planning the day). Always confirm what you recorded.
- Pre-bench journey: if they say they finished/prepared/updated their Endava Profile,
  ALWAYS call mark_my_profile_update_done this turn (it is idempotent — safe to call even
  if you think it is already done) and answer warmly that it is recorded; say you will
  write again in a few days to plan a successful bench.
- NEVER claim a task is already done from memory or chat history. When the person reports
  completing anything, call the matching mark tool NOW and confirm from its result. The
  database is the source of truth, not the conversation.
- If they accept planning their bench, start with the Mandatory courses first, then use
  get_study_suggestions to discuss certifications or courses that fit their Endava Profile.
- If they say they completed a named Mandatory, course, certification or workshop lab,
  call mark_my_task_done_by_title RIGHT AWAY with the title they mentioned, using their
  own words as the evidence. Mark it done first; do NOT withhold completion waiting for a
  link. Only if they said "the mandatory" without naming it, ask which one. After marking
  it done, you may invite them (optionally) to share a link or screenshot to enrich the
  record — but the task is already done.
- Surface blockers and deadline risks from the verified status. Suggest the next most
  valuable task (deadlines first).
- Answer in the person's language (Spanish or English). Be brief: this is chat.
"""


def make_tools(employee_email: str) -> list:
    """Build the toolset closed over the authenticated employee email."""

    NOT_ON_BENCH = ("This person is NOT on bench yet. Offer to set them up: show the "
                    "catalog (get_catalog), agree on role and track, then start_my_bench.")

    @tool
    def get_my_status() -> dict | str:
        """Verified progress for today: task statuses, follow-ups due, blockers and
        deadline risks. Computed deterministically — trust it over the chat history."""
        try:
            state = _load_bench_state(employee_email)
        except FileNotFoundError:
            return NOT_ON_BENCH
        track = _catalog.load_track(state["track_id"])
        return _verify_progress(state, track)

    @tool
    def get_my_plan() -> str:
        """The person's full bench plan (Markdown)."""
        try:
            state = _load_bench_state(employee_email)
        except FileNotFoundError:
            return NOT_ON_BENCH
        return _generate_bench_plan(
            state["employee_name"], employee_email,
            _catalog.load_profile(state["profile_id"]), _catalog.load_track(state["track_id"]))

    @tool
    def get_my_tasks() -> list[dict] | str:
        """The person's task instances with ids, statuses, deadlines and follow-up."""
        try:
            return _load_bench_state(employee_email)["tasks"]
        except FileNotFoundError:
            return NOT_ON_BENCH

    @tool
    def update_my_task(task_id: int, status: str, evidence: str = "", note: str = "") -> dict:
        """Record task progress the person reported. status: pending | in_progress |
        done | blocked. Put their reported proof (course %, commit URL) in evidence."""
        return _update_task_status(employee_email, task_id, status, evidence, note)

    @tool
    def mark_my_profile_update_done(evidence: str = "") -> dict:
        """Use when the person says their Endava Profile is ready, prepared, updated,
        finished or complete. Do not ask for a task id."""
        return _mark_profile_update_done(employee_email, evidence=evidence)

    @tool
    def mark_my_task_done_by_title(title: str, evidence: str = "") -> dict:
        """Use when the person says they completed a named task, mandatory course,
        certification or workshop lab. Pass the title they mentioned; do not ask for a task id."""
        return _mark_task_done_by_title(employee_email, title, evidence=evidence)

    @tool
    def record_my_check_in(period: str, planned: list[str] | None = None,
                           blockers: str = "") -> dict:
        """Register the daily check-in journal entry. period: 'am' (planning the day)
        or 'pm' (reporting completions). Include blockers verbatim."""
        return _record_check_in(employee_email, period, planned=planned, blockers=blockers)

    @tool
    def get_catalog() -> dict:
        """Available roles and bench tracks (for onboarding someone not on bench yet)."""
        return {
            "profiles": [{"id": p["id"], "name": p["name"]} for p in _catalog.list_profiles()],
            "tracks": [{"id": t["id"], "name": t["name"],
                        "target_profiles": t["target_profiles"]} for t in _catalog.list_tracks()],
        }

    @tool
    def start_my_bench(profile_id: str, track_id: str, my_name: str = "") -> str:
        """Put the person on bench with a role and track, instantiating their tasks.
        Confirm role and track with them before calling this."""
        state = _start_bench(my_name or employee_email, employee_email, profile_id, track_id)
        return f"Bench started with {len(state['tasks'])} tasks."

    @tool
    def get_my_profile() -> str:
        """The person's Endava Profile content (extracted from their PDF): background,
        skills, experience. Use it to personalize study and certification advice."""
        try:
            state = _load_bench_state(employee_email)
        except FileNotFoundError:
            return NOT_ON_BENCH
        return state.get("profile_text") or "No profile document uploaded yet."

    @tool
    def get_study_suggestions() -> dict | str:
        """Mandatory courses (must be completed, with the URL where completion must be
        registered), plus certifications and courses matched to the person's profile
        (e.g. AWS background -> AWS certs). Deterministic — do not invent additions."""
        from bench.tools.knowledge import suggest_for_profile

        try:
            state = _load_bench_state(employee_email)
        except FileNotFoundError:
            return NOT_ON_BENCH
        return suggest_for_profile(state.get("profile_text", ""))

    @tool
    def build_my_eod_report() -> str:
        """Generate and save today's EOD report (Markdown) for the responsibles."""
        try:
            state = _load_bench_state(employee_email)
        except FileNotFoundError:
            return NOT_ON_BENCH
        track = _catalog.load_track(state["track_id"])
        verification = _verify_progress(state, track)
        report = _build_eod_report(state, track, verification)
        _save_eod_report(report, employee_email, verification["date"])
        return report

    return [get_my_status, get_my_plan, get_my_tasks, update_my_task,
            mark_my_profile_update_done, mark_my_task_done_by_title, record_my_check_in,
            get_catalog, start_my_bench, get_my_profile, get_study_suggestions,
            build_my_eod_report]


def build_agent_graph(employee_email: str):
    """Agentic loop with conversation memory: llm <-> ToolNode until no tool calls."""
    model = ChatBedrockConverse(
        model_id=BEDROCK_MODEL_ID,
        region_name=BEDROCK_REGION,
    )
    tools = make_tools(employee_email)
    model_with_tools = model.bind_tools(tools)

    def llm_call(state: MessagesState):
        return {"messages": [model_with_tools.invoke(
            [SystemMessage(content=COACH_PROMPT)] + state["messages"])]}

    builder = StateGraph(MessagesState)
    builder.add_node("llm_call", llm_call)
    # handle_tool_errors: a failing tool becomes an error ToolMessage instead of
    # aborting mid-checkpoint (which would leave a dangling tool_use in the thread).
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", tools_condition)
    builder.add_edge("tools", "llm_call")
    return builder.compile(checkpointer=_CHECKPOINTER)


def run_chat(employee_email: str, text: str, thread_id: str | None = None) -> str:
    """One conversational turn with memory. thread_id = Teams conversation id.

    Self-repair: if a previous crash left a dangling `tool_use` in the thread
    (Bedrock ValidationException), the thread history is discarded and the turn
    retried fresh — losing chat memory beats a permanently broken conversation.
    """
    graph = build_agent_graph(employee_email)
    thread = thread_id or f"cli:{employee_email}"
    payload = {"messages": [{"role": "user", "content": text}]}
    try:
        result = graph.invoke(payload, config={"configurable": {"thread_id": thread}})
    except Exception as exc:
        if "tool_use" not in str(exc):
            raise
        try:
            _CHECKPOINTER.delete_thread(thread)
        except Exception:
            thread = f"{thread}:repaired"
        result = graph.invoke(payload, config={"configurable": {"thread_id": thread}})
    return result["messages"][-1].content


def main() -> None:
    require_bench_enabled()
    parser = argparse.ArgumentParser(prog="bench.agent_graph")
    parser.add_argument("--email", required=True)
    parser.add_argument("--ask", required=True)
    parser.add_argument("--thread", default=None)
    args = parser.parse_args()
    print(run_chat(args.email, args.ask, args.thread))


if __name__ == "__main__":
    main()
