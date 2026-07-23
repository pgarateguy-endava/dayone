"""Bench service API — consumed by the Teams bot (and any other channel). ADR 0004.

Contract: JSON in, `{"reply": "<markdown>"}` out. The channel posts the reply verbatim.
Intent routing: known commands hit deterministic tools/graphs; freeform text goes to the
agentic graph (Bedrock) when available, with a deterministic fallback otherwise.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from bench.actor import actor_context
from bench.config import api_token
from bench.graph import build_graph
from bench.tools import catalog
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.knowledge import suggest_for_profile
from bench.tools.state import (
    load_bench_state,
    mark_profile_update_done,
    mark_task_done_by_title,
    start_bench,
    update_task_status,
)
from bench.tools.verify_goals import verify_progress

def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Shared-secret gate for the whole service API. When BENCH_API_TOKEN is unset the
    API is open (local dev, tests); when set, callers must send
    `Authorization: Bearer <token>`. The Teams bot sends the same value."""
    token = api_token()
    if token is None:
        return
    if authorization != f"Bearer {token}":
        raise HTTPException(401, detail="Missing or invalid API token.")


async def establish_actor_context() -> AsyncIterator[str]:
    """Keep API operations inside the shared environment-derived actor context."""
    with actor_context() as actor:
        yield actor


router = APIRouter(prefix="/api/v1", tags=["bench-api"],
                   dependencies=[Depends(require_api_token), Depends(establish_actor_context)])


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
        return load_bench_state(_email_key(email))
    except FileNotFoundError:
        raise HTTPException(404, detail=f"'{email}' is not on bench. Use /onboard first.")


def _email_key(email: str) -> str:
    return email.strip().lower()


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


def _plain_text(text: str) -> str:
    return (
        text.strip().lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
    )


def _looks_like_profile_done(text: str) -> bool:
    plain = _plain_text(text)
    has_profile = "profile" in plain or "perfil" in plain
    done_words = (
        "termine", "prepare", "actualice", "complete", "finalice",
        "listo", "hecho", "ready", "done",
    )
    return has_profile and any(word in plain for word in done_words)


def _looks_like_named_task_done(text: str) -> bool:
    plain = _plain_text(text)
    done_words = (
        "termine", "hice", "complete", "finalice", "aprobie",
        "listo", "done", "finished", "completed",
    )
    named_hints = (
        "claude", "aws", "azure", "bedrock", "serverless", "react",
        "certification", "certificacion", "learning path", "lab",
    )
    return any(word in plain for word in done_words) and any(hint in plain for hint in named_hints)


def _last_delivered_notification_kind(email: str) -> str | None:
    from bench.notify import notification_log

    for notification in notification_log(_email_key(email)):
        if notification["delivered_at"]:
            return notification["kind"]
    return None


def _looks_like_planning_acceptance(text: str, email: str) -> bool:
    plain = _plain_text(text)
    if any(word in plain for word in ("planificar", "planifiquemos", "bench exitoso")):
        return True
    affirmatives = {"si", "dale", "ok", "okay", "claro", "vamos", "yes"}
    accepted = plain in affirmatives or plain.startswith("me parece")
    return accepted and _last_delivered_notification_kind(email) == "planning_prompt"


def _fmt_study_items(items: list[dict]) -> str:
    lines = []
    for item in items:
        line = f"- **{item['title']}**" + (f" ({item['provider']})" if item["provider"] else "")
        if item["url"]:
            line += f" — {item['url']}"
        if item["register_url"]:
            line += f"\n  Al terminarlo, registralo acá: {item['register_url']}"
        lines.append(line)
    return "\n".join(lines) or "- Lo revisamos juntos cuando tengas más contexto del Profile."


def _planning_reply(state: dict) -> str:
    suggestions = suggest_for_profile(state.get("profile_text", ""))
    return (
        "Excelente. Para planificar un bench exitoso, empecemos simple:\n\n"
        f"**1. Mandatory primero**\n{_fmt_study_items(suggestions['mandatory'])}\n\n"
        "**2. Después elegimos el camino**\n"
        "Con tu Endava Profile miramos qué certificaciones o cursos convienen más para tu perfil.\n\n"
        f"**Certificaciones sugeridas:**\n{_fmt_study_items(suggestions['certifications'])}\n\n"
        "Si querés, contame por cuál Mandatory querés empezar y lo registramos como tu primer foco."
    )


class ConversationRefIn(BaseModel):
    email: str
    conversation_id: str


@router.post("/conversation_ref")
def register_conversation_ref(body: ConversationRefIn):
    """The bot registers where each person talks, enabling proactive messages."""
    from bench.notify import save_conversation_ref

    save_conversation_ref(_email_key(body.email), body.conversation_id)
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
        state = start_bench(body.employee_name, _email_key(body.employee_email),
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
    employee_email = _email_key(body.employee_email)
    _state_or_404(employee_email)
    try:
        update_task_status(employee_email, body.task_id, body.status,
                           body.evidence, body.note)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, detail=str(exc))
    return {"reply": f"Task #{body.task_id} updated to **{body.status}**."}


@router.post("/checkin")
def checkin(body: CheckinIn):
    employee_email = _email_key(body.employee_email)
    _state_or_404(employee_email)
    if body.period not in ("am", "pm"):
        raise HTTPException(400, detail="period must be 'am' or 'pm'")
    result = build_graph().invoke({
        "employee_email": employee_email, "period": body.period,
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
    employee_email = _email_key(body.employee_email)
    try:
        state = load_bench_state(employee_email)
    except FileNotFoundError:
        return ("No estás en bench todavía y el chat con IA no está disponible. "
                "Pedile a tu People Lead que te dé de alta desde el backoffice web.")
    text = _plain_text(body.text)
    if _looks_like_profile_done(body.text):
        result = mark_profile_update_done(employee_email, evidence=body.text.strip())
        return (f"Excelente, lo dejo registrado: **{result['title']}** quedó como done. "
                "En unos días te escribiré para planificar un bench exitoso.")
    if _looks_like_named_task_done(body.text):
        try:
            result = mark_task_done_by_title(employee_email, body.text.strip(), evidence=body.text.strip())
            return (f"Excelente, lo dejo registrado: **{result['title']}** quedó como done. "
                    "Buen avance.")
        except KeyError:
            pass
    if text in ("plan", "my plan", "mi plan"):
        return _plan_reply(state)
    if text in ("tasks", "tareas", "mis tareas"):
        return _tasks_reply(state)
    if text in ("report", "reporte", "summary", "resumen", "eod"):
        return _report_reply(state)
    if _looks_like_planning_acceptance(body.text, employee_email):
        return _planning_reply(state)
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

        return {"reply": run_chat(_email_key(body.employee_email), body.text, body.conversation_id)}
    except (ImportError, SystemExit) as exc:
        # Agentic extras or AWS access not configured — expected in deterministic mode.
        print(f"[chat] agent unavailable ({exc}); serving deterministic reply")
        return {"reply": _deterministic_fallback(body)}
    except Exception as exc:
        # Unexpected agent failure — log loudly, but keep the channel alive.
        import traceback

        print(f"[chat] UNEXPECTED agent error: {exc!r}; serving deterministic reply")
        traceback.print_exc()
        return {"reply": _deterministic_fallback(body)}
