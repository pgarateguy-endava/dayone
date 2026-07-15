"""Bench service API — consumed by the Teams bot (and any other channel). ADR 0004.

Contract: JSON in, `{"reply": "<markdown>"}` out. The channel posts the reply verbatim.
Intent routing: known commands hit deterministic tools/graphs; freeform text goes to the
agentic graph (Bedrock) when available, with a deterministic fallback otherwise.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bench.graph import build_graph
from bench.tools import catalog
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.state import load_bench_state, start_bench, update_task_status
from bench.tools.verify_goals import verify_progress

router = APIRouter(prefix="/api/v1", tags=["bench-api"])


class OnboardIn(BaseModel):
    employee_name: str
    employee_email: str
    profile_id: str
    track_id: str


class ChatIn(BaseModel):
    employee_email: str
    text: str
    conversation_id: str | None = None


class CheckinIn(BaseModel):
    employee_email: str
    period: str  # "am" | "pm"
    planned: list[str] = []
    blockers: str = ""
    task_updates: list[dict] = []  # [{"task_id": int, "status": str, "evidence": str}]


class TaskUpdateIn(BaseModel):
    employee_email: str
    task_id: int
    status: str
    evidence: str = ""
    note: str = ""


def _state_or_404(email: str) -> dict:
    try:
        return load_bench_state(email)
    except FileNotFoundError:
        raise HTTPException(404, detail=f"'{email}' is not on bench. Use /onboard first.")


def _plan_reply(state: dict) -> str:
    profile = catalog.load_profile(state["profile_id"])
    track = catalog.load_track(state["track_id"])
    return generate_bench_plan(state["employee_name"], state["employee_email"], profile, track)


def _tasks_reply(state: dict) -> str:
    lines = ["**Your tasks:**", ""]
    for task in state["tasks"]:
        due = f", due {task['due_date']}" if task["due_date"] else ""
        lines.append(f"- #{task['task_id']} [{task['status']}] {task['title']}"
                     f" ({task['category']}{due})")
    return "\n".join(lines)


def _report_reply(state: dict) -> str:
    track = catalog.load_track(state["track_id"])
    verification = verify_progress(state, track)
    report = build_eod_report(state, track, verification)
    save_eod_report(report, state["employee_email"], verification["date"])
    return report


def _status_reply(state: dict) -> str:
    track = catalog.load_track(state["track_id"])
    verification = verify_progress(state, track)
    risky = [d for d in verification["deadlines"] if d["level"] in ("overdue", "at_risk")]
    lines = [
        f"**{state['employee_name']}** — {verification['tasks_done']}/"
        f"{verification['tasks_total']} tasks done "
        f"({int(verification['completion_rate'] * 100)}%).",
        f"Today: {verification['touched_today']} touched / "
        f"{verification['pending_today']} pending follow-ups.",
    ]
    if verification["blockers"]:
        lines.append("Blockers: " + "; ".join(verification["blockers"]))
    for deadline in risky:
        lines.append(f"⚠ {deadline['title']} — due {deadline['due']} ({deadline['level']})")
    return "\n".join(lines)


class ConversationRefIn(BaseModel):
    email: str
    conversation_id: str


@router.post("/conversation_ref")
def register_conversation_ref(body: ConversationRefIn):
    """The bot registers where each person talks, enabling proactive messages."""
    from bench.notify import save_conversation_ref

    save_conversation_ref(body.email, body.conversation_id)
    return {"ok": True}


@router.get("/notifications/pending")
def get_pending_notifications():
    from bench.notify import pending_notifications

    return {"notifications": pending_notifications()}


@router.post("/notifications/{notification_id}/delivered")
def notification_delivered(notification_id: int):
    from bench.notify import mark_delivered

    mark_delivered(notification_id)
    return {"ok": True}


@router.get("/catalog")
def get_catalog():
    return {
        "profiles": [{"id": p["id"], "name": p["name"]} for p in catalog.list_profiles()],
        "tracks": [{"id": t["id"], "name": t["name"],
                    "target_profiles": t["target_profiles"]} for t in catalog.list_tracks()],
    }


@router.post("/onboard")
def onboard(body: OnboardIn):
    try:
        state = start_bench(body.employee_name, body.employee_email,
                            body.profile_id, body.track_id)
    except KeyError as exc:
        raise HTTPException(400, detail=str(exc))
    return {"reply": _plan_reply(state)}


@router.get("/plan/{email}")
def plan(email: str):
    return {"reply": _plan_reply(_state_or_404(email))}


@router.get("/tasks/{email}")
def tasks(email: str):
    return {"reply": _tasks_reply(_state_or_404(email))}


@router.get("/report/{email}")
def report(email: str):
    return {"reply": _report_reply(_state_or_404(email))}


@router.post("/task")
def task_update(body: TaskUpdateIn):
    _state_or_404(body.employee_email)
    try:
        update_task_status(body.employee_email, body.task_id, body.status,
                           body.evidence, body.note)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, detail=str(exc))
    return {"reply": f"Task #{body.task_id} updated to **{body.status}**."}


@router.post("/checkin")
def checkin(body: CheckinIn):
    _state_or_404(body.employee_email)
    if body.period not in ("am", "pm"):
        raise HTTPException(400, detail="period must be 'am' or 'pm'")
    result = build_graph().invoke({
        "employee_email": body.employee_email, "period": body.period,
        "planned": body.planned, "blockers": body.blockers,
        "task_updates": body.task_updates,
    })
    if body.period == "pm":
        return {"reply": result["report_md"]}
    verification = result["verification"]
    goals = "\n".join(f"- #{f['task_id']} [{f['status']}] {f['title']}"
                      for f in verification["follow_up_today"])
    return {"reply": f"AM check-in recorded. Tasks to follow up today:\n\n{goals}"}


def _deterministic_fallback(body: ChatIn) -> str:
    """When Bedrock/langchain is unavailable the channel still works: a few keyword
    shortcuts over the deterministic tools, plus the verified status."""
    try:
        state = load_bench_state(body.employee_email)
    except FileNotFoundError:
        return ("No estás en bench todavía y el chat con IA no está disponible. "
                "Pedile a tu People Lead que te dé de alta desde el backoffice web.")
    text = body.text.strip().lower()
    if text in ("plan", "my plan", "mi plan"):
        return _plan_reply(state)
    if text in ("tasks", "tareas", "mis tareas"):
        return _tasks_reply(state)
    if text in ("report", "reporte", "summary", "resumen", "eod"):
        return _report_reply(state)
    return (_status_reply(state)
            + "\n\n_(Chat con IA no disponible — este es tu estado verificado. "
              "Atajos: `plan`, `tasks`, `report`.)_")


@router.post("/chat")
def chat(body: ChatIn):
    """Conversational-first (ADR 0004): every message goes to the agent, which leads
    using its tools (bound server-side to this employee). Deterministic fallback keeps
    the channel alive without AWS."""
    try:
        from bench.agent_graph import run_chat  # needs langchain-aws + AWS creds

        return {"reply": run_chat(body.employee_email, body.text, body.conversation_id)}
    except (SystemExit, Exception) as exc:
        import traceback

        print(f"[chat] AI unavailable, using deterministic fallback: {exc!r}")
        traceback.print_exc()
        return {"reply": _deterministic_fallback(body)}
