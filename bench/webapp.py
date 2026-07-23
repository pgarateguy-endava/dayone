"""Bench Assistant — dev web UI (FastAPI + htmx) over the SQLite catalog.

Views:
- /            responsibles dashboard (everyone on bench, progress, blockers, deadline risk)
- /review      employee review tree (select a person, inspect task progress/evidence)
- /onboard     assign a person to bench (employee + profile + track)
- /person/...  person cycle: task board with status/evidence, AM/PM check-in, EOD report
- /roles       ABM of roles (inline edit/delete) — context the AI uses for access boundaries
- /tracks      internal track ABM; hidden from main nav for the demo

Run:
    BENCH_ENABLED=1 uv run --group ui uvicorn bench.webapp:app --reload
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, Form, Request
    from fastapi.responses import HTMLResponse, RedirectResponse
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The web UI needs FastAPI. Install with: uv sync --group ui") from exc


def esc(value: object) -> str:
    """HTML-escape any DB/user-derived value before it goes into markup (quotes too, so
    it is safe inside attributes). The deterministic plan/report markdown rendered via
    marked.js is a separate, intentional path and is not routed through here."""
    return html.escape("" if value is None else str(value), quote=True)

from bench.config import bench_enabled
from bench.actor import actor_context, current_actor
from bench.db import FOLLOW_UP_OPTIONS, TASK_CATEGORIES, TASK_STATUSES
from bench.graph import build_graph
from bench.seed import seed_if_empty
from bench.tools import catalog
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.state import (
    list_bench_people,
    load_bench_state,
    start_bench,
    update_task_status,
)
from bench.tools.verify_goals import FOLLOW_UP_LABELS, verify_progress

from bench.api import router as api_router

async def _proactive_loop():
    """Every 60s: evaluate proactive rules (pre-bench greeting, kickoff, weekly
    progress check) and queue notifications; the bot polls and delivers them."""
    import asyncio

    from bench.notify import generate_due_notifications

    while True:
        try:
            if bench_enabled():
                with actor_context():
                    queued = generate_due_notifications()
                if queued:
                    print(f"[notify] queued {queued} proactive notification(s)")
        except Exception as exc:
            print(f"[notify] scheduler error: {exc!r}")
        await asyncio.sleep(60)


@asynccontextmanager
async def _lifespan(_app: "FastAPI"):
    import asyncio

    task = asyncio.create_task(_proactive_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Bench Assistant (dev UI)", lifespan=_lifespan)
app.include_router(api_router)  # /api/v1 — consumed by the Teams bot (ADR 0004)

CATEGORY_LABELS = {
    "course": "Courses",
    "certification": "Certifications",
    "profile_update": "Endava Profile",
    "portfolio": "Workshop - LABS",
    "admin": "Admin",
}

_CSS = """
:root { --ink:#1b1b25; --paper:#f7f6f3; --card:#fff; --line:#e8e6e1; --accent:#ff4a1c; --accent-dark:#d63a12; --muted:#75717a; }
* { box-sizing: border-box; }
body { font-family: -apple-system, 'Segoe UI', Inter, system-ui, sans-serif; margin: 0; background: var(--paper); color: var(--ink); font-size: 15px; }
nav { background: var(--ink); color: #fff; padding: 14px 32px; display: flex; gap: 26px; align-items: center; position: sticky; top: 0; z-index: 5; }
nav::before { content: 'Bench Assistant'; font-weight: 800; color: var(--accent); margin-right: 14px; letter-spacing: .3px; }
nav a { color: #cfccd6; text-decoration: none; font-weight: 600; font-size: 14px; padding: 4px 2px; border-bottom: 2px solid transparent; }
nav a:hover { color: #fff; border-bottom-color: var(--accent); }
main { max-width: 1150px; margin: 30px auto; padding: 0 20px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 22px 26px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(27,27,37,.05); }
table { border-collapse: collapse; width: 100%; }
th { text-align: left; padding: 10px; font-size: 12px; text-transform: uppercase; letter-spacing: .6px; color: var(--muted); border-bottom: 2px solid var(--line); }
td { text-align: left; padding: 12px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
tr:hover td { background: #fbfaf8; }
.badge { padding: 3px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.ok { background: #e5f6ec; color: #14683a; } .warn { background: #fdf3d7; color: #8a6116; }
.bad { background: #fde8e4; color: #a52a12; } .info { background: #e9e7fd; color: #4438a8; }
input, select, textarea { padding: 8px 10px; margin: 2px 0; border: 1px solid #d7d4cd; border-radius: 8px; font: inherit; background: #fff; }
input:focus, select:focus, textarea:focus { outline: 2px solid var(--accent); outline-offset: 0; border-color: var(--accent); }
form.block input, form.block select, form.block textarea { width: 100%; margin-bottom: 12px; }
label { font-weight: 600; font-size: 13px; color: var(--muted); }
button { background: var(--ink); color: #fff; border: 0; border-radius: 8px; padding: 8px 18px; font-weight: 700; cursor: pointer; font-size: 14px; }
button:hover { background: #000; }
button.danger { background: #fff; color: var(--accent-dark); border: 1px solid var(--accent-dark); }
button.danger:hover { background: var(--accent-dark); color: #fff; }
button.ghost { background: #fff; color: var(--muted); border: 1px solid var(--line); }
button.add { background: var(--accent); border-radius: 999px; font-size: 14px; }
button.add:hover { background: var(--accent-dark); }
h1 { font-size: 26px; font-weight: 800; letter-spacing: -.3px; } h2 { font-size: 16px; font-weight: 700; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
a { color: var(--accent-dark); text-decoration: none; font-weight: 600; } a:hover { text-decoration: underline; }
small { color: var(--muted); }
tr.editing td { background: #fff7f4; }
dialog { border: 1px solid var(--line); border-radius: 16px; padding: 26px 30px; min-width: 480px; max-width: 660px; box-shadow: 0 18px 50px rgba(27,27,37,.25); }
dialog::backdrop { background: rgba(27,27,37,.5); }
dialog h2 { margin-top: 0; }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 14px; }
.review-select { display: flex; gap: 12px; align-items: end; flex-wrap: wrap; }
.review-select select { min-width: 320px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 12px; }
.metric { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; background: #fbfaf8; }
.metric b { display: block; font-size: 20px; margin-bottom: 4px; }
.tree { list-style: none; padding: 0; margin: 0; }
.tree details { border-top: 1px solid var(--line); padding: 12px 0; }
.tree details:first-child { border-top: 0; }
.tree summary { cursor: pointer; font-weight: 800; display: flex; align-items: center; gap: 10px; }
.tree ul { list-style: none; padding-left: 20px; margin: 10px 0 0; border-left: 2px solid var(--line); }
.tree li { padding: 10px 0 10px 14px; }
.tree .task-title { font-weight: 750; }
.task-meta { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 4px; color: var(--muted); font-size: 13px; }
.evidence { margin-top: 5px; color: var(--ink); font-size: 13px; }
"""


def _modal(modal_id: str, button_label: str, title: str, form_html: str) -> str:
    """A '+' button that opens a native <dialog> modal containing the given form."""
    return f"""<button class="add" onclick="document.getElementById('{modal_id}').showModal()">＋ {button_label}</button>
<dialog id="{modal_id}"><h2>{title}</h2>{form_html}
<button type="button" class="ghost" onclick="document.getElementById('{modal_id}').close()">Cancel</button>
</dialog>"""


def _page(title: str, body: str) -> HTMLResponse:
    title = esc(title)  # body is intentional HTML; the title is always plain text
    return HTMLResponse(f"""<!doctype html><html><head><meta charset="utf-8">
<title>{title} · Bench Assistant</title>
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>{_CSS}</style></head><body>
<nav><span class="actor-context">Operator: {esc(current_actor())}</span><a href="/">Dashboard</a><a href="/review">Review</a><a href="/onboard">Onboard to bench</a>
<a href="/roles">Roles</a><a href="/knowledge">AI Knowledge</a></nav>
<main><h1>{title}</h1>{body}</main></body></html>""")


@app.middleware("http")
async def _flag_gate(request: Request, call_next):
    if not bench_enabled():
        return HTMLResponse("Bench domain is disabled. Set BENCH_ENABLED=1.", status_code=403)
    seed_if_empty()
    return await call_next(request)


@app.middleware("http")
async def _actor_context(request: Request, call_next):
    with actor_context():
        return await call_next(request)


def _progress_badge(verification: dict) -> str:
    rate = verification["completion_rate"]
    cls = "ok" if rate >= 0.99 else ("warn" if rate > 0 else "bad")
    return (f'<span class="badge {cls}">{verification["tasks_done"]}/{verification["tasks_total"]} done</span> '
            f'<span class="badge info">today {verification["touched_today"]}/'
            f'{verification["touched_today"] + verification["pending_today"]}</span>')


def _deadline_badge(verification: dict) -> str:
    levels = [d["level"] for d in verification["deadlines"]]
    if "overdue" in levels:
        return '<span class="badge bad">deadline overdue</span>'
    if "at_risk" in levels:
        return '<span class="badge warn">deadline at risk</span>'
    return '<span class="badge ok">deadlines ok</span>'


def _md(markdown_text: str, div_id: str) -> str:
    return (f'<div id="{div_id}"></div><script>document.getElementById("{div_id}").innerHTML = '
            f'marked.parse({json.dumps(markdown_text)});</script>')


def _status_badge(status: str) -> str:
    cls = {"done": "ok", "in_progress": "info", "blocked": "bad", "pending": "warn"}[status]
    return f'<span class="badge {cls}">{status}</span>'


# ---------- Dashboard ----------

@app.get("/", response_class=HTMLResponse)
def dashboard():
    rows = []
    for person in list_bench_people():
        state = load_bench_state(person["email"])
        track = catalog.load_track(person["track_id"])
        verification = verify_progress(state, track)
        blockers = f'<span class="badge bad">{len(verification["blockers"])} blocker(s)</span>' \
            if verification["blockers"] else ""
        from bench.tools.state import computed_status

        status = computed_status(person["bench_start_date"])
        status_cls = {"active": "ok", "pre_bench": "info", "inactive": "warn"}.get(status, "warn")
        start = esc(person["bench_start_date"] or "—")
        email = esc(person["email"])
        profile_doc = "📄" if person["profile_text"] else ""
        status_form = (
            f'<form method="post" action="/person/{email}/date" style="white-space:nowrap">'
            f'<input type="date" name="bench_start_date" value="{esc(person["bench_start_date"] or "")}">'
            f' <button>Set date</button></form>')
        rows.append(
            f'<tr><td><a href="/person/{email}">{esc(person["name"])}</a> {profile_doc}'
            f'<br><small>{email}</small></td>'
            f'<td>{esc(person["profile_id"])}<br><small>{esc(person["track_id"])}</small></td>'
            f'<td><span class="badge {status_cls}">{status}</span><br><small>starts {start}</small></td>'
            f'<td>{_progress_badge(verification)} {blockers}</td>'
            f'<td>{_deadline_badge(verification)}</td>'
            f'<td>AM {"✓" if verification["checked_in_am"] else "—"} / '
            f'PM {"✓" if verification["checked_in_pm"] else "—"}</td>'
            f'<td>{status_form}</td></tr>')
    table = ("<table><tr><th>Person</th><th>Role / Track</th><th>Status</th><th>Progress</th>"
             "<th>Deadlines</th><th>Check-ins</th><th>Activation</th></tr>"
             + "".join(rows) + "</table>") \
        if rows else "<p>Nobody on bench yet. <a href='/onboard'>Onboard someone</a>.</p>"
    from bench.notify import notification_log

    log_rows = "".join(
        f"<tr><td>{esc(n['created_at'][:16])}</td><td>{esc(n['email'])}</td>"
        f"<td><span class='badge info'>{esc(n['kind'])}</span></td>"
        f"<td>{'delivered' if n['delivered_at'] else 'pending'}</td></tr>"
        for n in notification_log()[:15])
    log = (f'<div class="card"><h2>Proactive contact log</h2>'
           f'<table><tr><th>When</th><th>Person</th><th>Kind</th><th>Delivery</th></tr>{log_rows}</table></div>'
           if log_rows else "")
    return _page("Bench dashboard", f'<div class="card">{table}</div>{log}')


def _task_review_item(task: dict) -> str:
    due = f'<span>due {esc(task["due_date"])}</span>' if task["due_date"] else ""
    evidence = (f'<div class="evidence"><b>Evidence:</b> {esc(task["evidence"])}</div>'
                if task["evidence"] else '<div class="evidence"><small>No evidence yet.</small></div>')
    note = (f'<div class="evidence"><b>Note:</b> {esc(task["progress_note"])}</div>'
            if task["progress_note"] else "")
    updated = f'<span>updated {esc(task["updated_at"][:10])}</span>' if task["updated_at"] else ""
    completed = f'<span>completed {esc(task["completed_at"][:10])}</span>' if task["completed_at"] else ""
    return f"""<li>
<div><span class="task-title">{esc(task['title'])}</span> {_status_badge(task['status'])}</div>
<div class="task-meta"><span>follow-up {esc(FOLLOW_UP_LABELS.get(task['follow_up'], task['follow_up']))}</span>
{due}{updated}{completed}</div>
{evidence}{note}
</li>"""


def _review_tree(tasks: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for task in tasks:
        grouped[task["category"]].append(task)
    sections = []
    for category in TASK_CATEGORIES:
        items = grouped.get(category, [])
        if not items:
            continue
        done = sum(1 for task in items if task["status"] == "done")
        rows = "".join(_task_review_item(task) for task in items)
        sections.append(
            f"""<details open><summary>{CATEGORY_LABELS.get(category, category)} <span class="badge info">{done}/{len(items)} done</span></summary>
<ul>{rows}</ul></details>""")
    return f'<ul class="tree">{"".join(sections)}</ul>' if sections else "<p>No tasks assigned.</p>"


@app.get("/review", response_class=HTMLResponse)
def review_by_employee(email: str = ""):
    people = list_bench_people()
    if not people:
        return _page("Review by employee",
                     "<div class='card'><p>Nobody on bench yet. "
                     "<a href='/onboard'>Onboard someone</a>.</p></div>")
    by_email = {p["email"].lower(): p for p in people}
    selected = by_email.get(email.lower(), people[0] if not email else None)
    if selected is None:
        selected = people[0]
    selected_email = selected["email"]
    state = load_bench_state(selected_email)
    track = catalog.load_track(state["track_id"])
    verification = verify_progress(state, track)
    from bench.tools.state import computed_status

    options = "".join(
        f'<option value="{esc(person["email"])}" {"selected" if person["email"] == selected_email else ""}>'
        f'{esc(person["name"])} - {esc(person["email"])}</option>'
        for person in people)
    selector = f"""<div class="card"><form class="review-select" method="get" action="/review">
<label>Employee<br><select name="email" onchange="this.form.submit()">{options}</select></label>
<button>Review</button>
<a href="/person/{esc(selected_email)}">Open editable board</a>
</form></div>"""
    status = computed_status(state["bench_start_date"])
    blockers = len(verification["blockers"])
    header = f"""<div class="card">
<div class="card-head"><h2>{esc(state['employee_name'])}</h2><span class="badge info">{status}</span></div>
<p><small>{esc(selected_email)} · {esc(state['profile_id'])} · {esc(state['track_id'])} · starts {esc(state['bench_start_date'] or 'not set')}</small></p>
<div class="summary-grid">
<div class="metric"><b>{verification['tasks_done']}/{verification['tasks_total']}</b><small>tasks done</small></div>
<div class="metric"><b>{verification['touched_today']}/{verification['touched_today'] + verification['pending_today']}</b><small>touched today</small></div>
<div class="metric"><b>{blockers}</b><small>blockers</small></div>
<div class="metric"><b>{sum(1 for d in verification['deadlines'] if d['level'] in ('overdue', 'at_risk'))}</b><small>deadline risks</small></div>
</div></div>"""
    blockers_card = ""
    if verification["blockers"]:
        blockers_card = ("<div class='card'><h2>Blockers</h2><ul>"
                         + "".join(f"<li>{esc(blocker)}</li>" for blocker in verification["blockers"])
                         + "</ul></div>")
    return _page("Review by employee",
                 selector + header + f"<div class='card'><h2>Task tree</h2>{_review_tree(state['tasks'])}</div>"
                 + blockers_card)


@app.post("/person/{email}/date")
def person_date(email: str, bench_start_date: str = Form("")):
    """Changing the date IS the trigger: history cleared, rules re-evaluated NOW."""
    from bench.notify import generate_due_notifications
    from bench.tools.state import set_bench_start_date

    set_bench_start_date(email, bench_start_date or None)
    generate_due_notifications()  # immediate — the bot delivers within its next poll (~20s)
    return RedirectResponse("/", status_code=303)


# ---------- Onboard ----------

@app.get("/onboard", response_class=HTMLResponse)
def onboard_form():
    options_p = "".join(f'<option value="{esc(p["id"])}">{esc(p["name"])}</option>'
                        for p in catalog.list_profiles())
    options_t = "".join(f'<option value="{esc(t["id"])}">{esc(t["name"])}</option>'
                        for t in catalog.list_tracks())
    return _page("Onboard to bench", f"""<div class="card">
<form class="block" method="post" action="/onboard" enctype="multipart/form-data">
<label>Name</label><input name="employee" required>
<label>Email</label><input name="email" type="email" required>
<label>Role (context for the AI — defines access boundaries)</label><select name="profile">{options_p}</select>
<label>Track (bench plan — tasks, deadlines, follow-up)</label><select name="track">{options_t}</select>
<label>Bench start date — THE activation trigger (empty = inactive; future = pre-bench
heads-up; today/past = active, kickoff message)</label>
<input name="bench_start_date" type="date">
<label>Endava Profile (PDF — gives the AI the person's background for suggestions)</label>
<input name="profile_pdf" type="file" accept="application/pdf">
<button>Create bench plan</button></form></div>""")


@app.post("/onboard")
async def onboard(request: Request):
    form = await request.form()
    profile_text, profile_filename = "", ""
    upload = form.get("profile_pdf")
    if upload is not None and getattr(upload, "filename", ""):
        from bench.tools.profile_pdf import extract_pdf_text

        profile_text = extract_pdf_text(await upload.read())
        profile_filename = upload.filename
    email = str(form["email"]).strip()
    start_bench(str(form["employee"]).strip(), email, str(form["profile"]), str(form["track"]),
                bench_start_date=str(form.get("bench_start_date") or "") or None,
                profile_text=profile_text, profile_filename=profile_filename)
    return RedirectResponse(f"/person/{email}", status_code=303)


# ---------- Person cycle ----------

def _person_task_row(email: str, task: dict) -> str:
    status_options = "".join(
        f'<option value="{s}" {"selected" if s == task["status"] else ""}>{s}</option>'
        for s in TASK_STATUSES)
    due = f'<br><small>due {esc(task["due_date"])}</small>' if task["due_date"] else ""
    contacts = "".join(
        f'<br><small>👤 {esc(c["name"])}{" — " + esc(c["note"]) if c["note"] else ""}</small>'
        for c in task.get("contacts", []))
    evidence_hint = "required" if task["evidence_required"] else "optional"
    return f"""<tr><td><b>{esc(task['title'])}</b><br><small>{esc(task['description'])}</small>{contacts}</td>
<td>{esc(task['category'])}{due}</td>
<td><small>{esc(FOLLOW_UP_LABELS.get(task['follow_up'], task['follow_up']))}</small></td>
<td>{_status_badge(task['status'])}</td>
<td><form method="post" action="/person/{esc(email)}/task/{task['task_id']}">
<select name="status">{status_options}</select>
<input name="evidence" placeholder="Evidence ({evidence_hint})" value="{esc(task['evidence'])}">
<button>Update</button></form></td></tr>"""


@app.get("/person/{email}", response_class=HTMLResponse)
def person_view(email: str):
    state = load_bench_state(email)
    profile = catalog.load_profile(state["profile_id"])
    track = catalog.load_track(state["track_id"])
    verification = verify_progress(state, track)
    plan = generate_bench_plan(state["employee_name"], email, profile, track)

    catalog_tasks = {t["id"]: t for t in track["tasks"]}
    for task in state["tasks"]:
        task["contacts"] = catalog_tasks.get(task["task_id"], {}).get("contacts", [])
    task_rows = "".join(_person_task_row(email, t) for t in state["tasks"])
    email_url = esc(email)

    body = f"""
<div class="card"><b>Today:</b> {_progress_badge(verification)} {_deadline_badge(verification)}
&nbsp; <a href="/person/{email_url}/report">Generate EOD report</a></div>
<div class="card"><h2>My tasks</h2>
<table><tr><th>Task</th><th>Category</th><th>Follow-up</th><th>Status</th><th>Update</th></tr>
{task_rows}</table></div>
<div class="cols">
<div class="card"><h2>AM check-in — plan the day</h2>
<form class="block" method="post" action="/person/{email_url}/checkin"><input type="hidden" name="period" value="am">
<label>What will you work on today?</label><textarea name="planned" rows="2"></textarea>
<label>Blockers</label><input name="blockers"><button>Check in (AM)</button></form></div>
<div class="card"><h2>PM check-in — close the day</h2>
<p><small>Update your tasks above first; the PM check-in verifies and reports.</small></p>
<form class="block" method="post" action="/person/{email_url}/checkin"><input type="hidden" name="period" value="pm">
<label>Blockers</label><input name="blockers"><button>Check in (PM) & send EOD report</button></form></div>
</div>
<div class="card"><h2>Bench plan</h2>{_md(plan, "plan")}</div>"""
    return _page(state["employee_name"], body)


@app.post("/person/{email}/task/{task_id}")
def person_task_update(email: str, task_id: int,
                       status: str = Form(...), evidence: str = Form("")):
    update_task_status(email, task_id, status, evidence=evidence)
    return RedirectResponse(f"/person/{email}", status_code=303)


@app.post("/person/{email}/checkin")
async def person_checkin(email: str, request: Request):
    form = await request.form()
    planned = [p for p in [str(form.get("planned", "")).strip()] if p]
    build_graph().invoke({
        "employee_email": email, "period": str(form["period"]),
        "task_updates": [], "planned": planned, "blockers": str(form.get("blockers", "")),
    })
    return RedirectResponse(f"/person/{email}", status_code=303)


@app.get("/person/{email}/report", response_class=HTMLResponse)
def person_report(email: str):
    state = load_bench_state(email)
    track = catalog.load_track(state["track_id"])
    verification = verify_progress(state, track)
    report = build_eod_report(state, track, verification)
    path = save_eod_report(report, email, verification["date"])
    return _page("EOD report", f'<div class="card">{_md(report, "report")}'
                               f'<p><i>Saved to {esc(path)} (simulated Teams delivery).</i></p></div>')


# ---------- Roles ABM ----------

def _role_row(profile: dict) -> str:
    pid = esc(profile['id'])
    perms = "<br>".join(f"<small><b>{esc(k)}:</b> {esc(', '.join(v))}</small>"
                        for k, v in profile["permissions"].items()) or "<small>—</small>"
    approvals = esc(", ".join(profile["approvals_required"])) or "—"
    return f"""<tr id="role-{pid}">
<td><b>{esc(profile['name'])}</b><br><small>{pid}</small></td>
<td>{esc(profile['summary'])}</td><td>{perms}</td><td><small>{approvals}</small></td>
<td style="white-space:nowrap">
<button hx-get="/roles/{pid}/edit" hx-target="#role-{pid}" hx-swap="outerHTML">Edit</button>
<button class="danger" hx-post="/roles/{pid}/delete" hx-target="#role-{pid}"
 hx-swap="outerHTML" hx-confirm="Delete role {pid}?">Delete</button></td></tr>"""


def _role_edit_row(profile: dict) -> str:
    pid = esc(profile['id'])
    perms_text = esc("\n".join(f"{k}: {v}" for k, values in profile["permissions"].items()
                              for v in values))
    approvals_text = esc("\n".join(profile["approvals_required"]))
    return f"""<tr id="role-{pid}" class="editing">
<td colspan="5"><form hx-post="/roles/{pid}" hx-target="#role-{pid}" hx-swap="outerHTML">
<b>{pid}</b><br>
<input name="name" value="{esc(profile['name'])}" placeholder="Name" style="width:30%">
<input name="summary" value="{esc(profile['summary'])}" placeholder="Summary" style="width:60%"><br>
<textarea name="permissions" rows="4" placeholder="aws: staging-read" style="width:45%">{perms_text}</textarea>
<textarea name="approvals" rows="4" placeholder="prod-write" style="width:45%">{approvals_text}</textarea><br>
<button>Save</button>
<button type="button" class="ghost" hx-get="/roles/{pid}/row"
 hx-target="#role-{pid}" hx-swap="outerHTML">Cancel</button>
</form></td></tr>"""


def _parse_permissions(text: str) -> list[tuple[str, str]]:
    rows = []
    for line in text.splitlines():
        kind, _, value = line.partition(":")
        if kind.strip() and value.strip():
            rows.append((kind.strip(), value.strip()))
    return rows


@app.get("/roles", response_class=HTMLResponse)
def roles_list():
    rows = "".join(_role_row(p) for p in catalog.list_profiles())
    new_role_form = """<form class="block" method="post" action="/roles">
<label>Id (e.g. senior-qa)</label><input name="profile_id" required>
<label>Name</label><input name="name" required>
<label>Summary</label><input name="summary">
<label>Permissions (one per line, "kind: value" — kinds: aws, ci_cd, repositories)</label>
<textarea name="permissions" rows="3"></textarea>
<label>Actions needing approval (one per line)</label><textarea name="approvals" rows="2"></textarea>
<button>Create role</button></form>"""
    body = f"""<div class="card">
<div class="card-head">
<p><small>Roles give the AI context: what the person is, their access boundaries and what
needs human approval. More content per role can be added later (skills matrix, seniority).</small></p>
{_modal("new-role", "New role", "New role", new_role_form)}
</div>
<table><tr><th>Role</th><th>Summary</th><th>Access</th><th>Needs approval</th><th></th></tr>
{rows}</table></div>"""
    return _page("Roles", body)


@app.post("/roles")
def roles_create(profile_id: str = Form(...), name: str = Form(...), summary: str = Form(""),
                 permissions: str = Form(""), approvals: str = Form("")):
    catalog.upsert_profile(profile_id.strip(), name.strip(), summary.strip(),
                           _parse_permissions(permissions),
                           [line.strip() for line in approvals.splitlines() if line.strip()])
    return RedirectResponse("/roles", status_code=303)


@app.get("/roles/{profile_id}/row", response_class=HTMLResponse)
def role_row(profile_id: str):
    return HTMLResponse(_role_row(catalog.load_profile(profile_id)))


@app.get("/roles/{profile_id}/edit", response_class=HTMLResponse)
def role_edit(profile_id: str):
    return HTMLResponse(_role_edit_row(catalog.load_profile(profile_id)))


@app.post("/roles/{profile_id}", response_class=HTMLResponse)
def role_save(profile_id: str, name: str = Form(...), summary: str = Form(""),
              permissions: str = Form(""), approvals: str = Form("")):
    catalog.upsert_profile(profile_id, name.strip(), summary.strip(),
                           _parse_permissions(permissions),
                           [line.strip() for line in approvals.splitlines() if line.strip()])
    return HTMLResponse(_role_row(catalog.load_profile(profile_id)))


@app.post("/roles/{profile_id}/delete", response_class=HTMLResponse)
def role_delete(profile_id: str):
    try:
        catalog.delete_profile(profile_id)
        return HTMLResponse("")
    except ValueError as exc:
        profile = catalog.load_profile(profile_id)
        row = _role_row(profile)
        return HTMLResponse(row.replace("</td></tr>",
                                        f'<br><span class="badge bad">{esc(exc)}</span></td></tr>'))


# ---------- Tracks ABM ----------

@app.get("/tracks", response_class=HTMLResponse)
def tracks_list():
    rows = []
    for track in catalog.list_tracks():
        tid = esc(track['id'])
        rows.append(f"""<tr id="track-{tid}">
<td><a href="/tracks/{tid}"><b>{esc(track['name'])}</b></a><br><small>{tid}</small></td>
<td>{esc(track['duration_weeks'])} weeks</td>
<td>{esc(', '.join(track['target_profiles'])) or '—'}</td>
<td>{len(track['tasks'])} tasks</td>
<td><button class="danger" hx-post="/tracks/{tid}/delete" hx-target="#track-{tid}"
 hx-swap="outerHTML" hx-confirm="Delete track {tid} and its tasks?">Delete</button></td></tr>""")
    role_checks = "".join(
        f'<label style="margin-right:12px"><input type="checkbox" name="profiles" value="{esc(p["id"])}" '
        f'style="width:auto"> {esc(p["name"])}</label>' for p in catalog.list_profiles())
    new_track_form = f"""<form class="block" method="post" action="/tracks">
<label>Id (e.g. qa-automation-track)</label><input name="track_id" required>
<label>Name</label><input name="name" required>
<label>Duration (weeks)</label><input name="duration_weeks" type="number" value="4">
<label>For roles</label><div>{role_checks}</div><br>
<button>Create track</button></form>"""
    body = f"""<div class="card">
<div class="card-head"><h2>Tracks</h2>{_modal("new-track", "New track", "New track", new_track_form)}</div>
<table><tr><th>Track</th><th>Duration</th><th>For roles</th><th>Tasks</th><th></th></tr>
{''.join(rows)}</table></div>"""
    return _page("Tracks", body)


@app.post("/tracks")
async def tracks_create(request: Request):
    form = await request.form()
    catalog.create_track(str(form["track_id"]).strip(), str(form["name"]).strip(),
                         int(str(form.get("duration_weeks", "4"))), form.getlist("profiles"))
    return RedirectResponse(f"/tracks/{str(form['track_id']).strip()}", status_code=303)


@app.post("/tracks/{track_id}/delete", response_class=HTMLResponse)
def track_delete(track_id: str):
    try:
        catalog.delete_track(track_id)
        return HTMLResponse("")
    except ValueError as exc:
        return HTMLResponse(f'<tr id="track-{esc(track_id)}"><td colspan="5">'
                            f'<span class="badge bad">{esc(exc)}</span></td></tr>')


def _task_row(task: dict) -> str:
    contact = task["contacts"][0] if task["contacts"] else None
    contact_html = (f'<br><small>👤 {esc(contact["name"])}'
                    f'{" — " + esc(contact["note"]) if contact["note"] else ""}</small>') if contact else ""
    return f"""<tr id="task-{task['id']}">
<td><b>{esc(task['title'])}</b><br><small>{esc(task['description'])}</small>{contact_html}</td>
<td>{esc(task['category'])}</td><td>{esc(task['due_date'] or '—')}</td>
<td>{esc(FOLLOW_UP_LABELS.get(task['follow_up'], task['follow_up']))}</td>
<td>{esc(task['est_hours'] or '—')}</td><td>{'yes' if task['requires_approval'] else 'no'}</td>
<td style="white-space:nowrap">
<button hx-get="/tasks/{task['id']}/edit" hx-target="#task-{task['id']}" hx-swap="outerHTML">Edit</button>
<button class="danger" hx-post="/tasks/{task['id']}/delete" hx-target="#task-{task['id']}"
 hx-swap="outerHTML" hx-confirm="Delete task '{esc(task['title'])}'?">Delete</button></td></tr>"""


def _task_edit_row(task: dict) -> str:
    contact = task["contacts"][0] if task["contacts"] else {"name": "", "note": ""}
    category_options = "".join(
        f'<option value="{c}" {"selected" if c == task["category"] else ""}>{c}</option>'
        for c in TASK_CATEGORIES)
    follow_options = "".join(
        f'<option value="{f}" {"selected" if f == task["follow_up"] else ""}>{FOLLOW_UP_LABELS[f]}</option>'
        for f in FOLLOW_UP_OPTIONS)
    return f"""<tr id="task-{task['id']}" class="editing">
<td colspan="7"><form hx-post="/tasks/{task['id']}" hx-target="#task-{task['id']}" hx-swap="outerHTML">
<input name="title" value="{esc(task['title'])}" placeholder="Task" style="width:32%" required>
<input name="description" value="{esc(task['description'])}" placeholder="Description" style="width:55%"><br>
<select name="category">{category_options}</select>
<input name="due_date" type="date" value="{esc(task['due_date'] or '')}">
<select name="follow_up">{follow_options}</select>
<input name="est_hours" type="number" step="0.5" value="{esc(task['est_hours'] or '')}" placeholder="h" style="width:70px">
<input name="link" value="{esc(task['link'])}" placeholder="Link" style="width:20%">
<label style="white-space:nowrap"><input type="checkbox" name="requires_approval" style="width:auto"
 {'checked' if task['requires_approval'] else ''}> needs approval</label><br>
<input name="contact_name" value="{esc(contact['name'])}" placeholder="Contact (optional)">
<input name="contact_note" value="{esc(contact['note'])}" placeholder="Why this contact" style="width:40%">
<button>Save</button>
<button type="button" class="ghost" hx-get="/tasks/{task['id']}/row"
 hx-target="#task-{task['id']}" hx-swap="outerHTML">Cancel</button>
</form></td></tr>"""


def _task_modal_card(track_id: str, rows: str, category_options: str, follow_options: str) -> str:
    track_id = esc(track_id)
    add_task_form = f"""<form class="block" method="post" action="/tracks/{track_id}/tasks">
<label>Task</label><input name="title" required>
<label>Description</label><input name="description">
<label>Category</label><select name="category">{category_options}</select>
<label>Deadline</label><input name="due_date" type="date">
<label>AI follow-up frequency</label><select name="follow_up">{follow_options}</select>
<label>Estimated hours</label><input name="est_hours" type="number" step="0.5">
<label>Link (course / doc)</label><input name="link">
<label>Contact (optional)</label><input name="contact_name">
<label>Why this contact</label><input name="contact_note">
<label><input type="checkbox" name="requires_approval" style="width:auto"> needs approval</label><br><br>
<button>Add task</button></form>"""
    return f"""<div class="card">
<div class="card-head"><h2>Tasks</h2>{_modal("new-task", "Add task", "Add task", add_task_form)}</div>
<table><tr><th>Task</th><th>Category</th><th>Deadline</th><th>Follow-up</th><th>Est. h</th><th>Approval</th><th></th></tr>
{rows}</table></div>"""


def _responsibles_card(track_id: str, responsibles: str) -> str:
    track_id = esc(track_id)
    add_responsible_form = f"""<form class="block" method="post" action="/tracks/{track_id}/responsibles">
<label>Name</label><input name="name" required>
<label>Email</label><input name="email" type="email" required>
<label>Role</label>
<select name="role"><option>people-lead</option><option>resourcing</option><option>capability-lead</option></select>
<button>Add responsible</button></form>"""
    return f"""<div class="card">
<div class="card-head"><h2>Responsibles (receive the EOD report)</h2>
{_modal("new-resp", "Add responsible", "Add responsible", add_responsible_form)}</div>
<ul>{responsibles or '<li>None yet.</li>'}</ul></div>"""


@app.get("/tracks/{track_id}", response_class=HTMLResponse)
def track_detail(track_id: str):
    track = catalog.load_track(track_id)
    rows = "".join(_task_row(t) for t in track["tasks"])
    role_checks = "".join(
        f'<label style="margin-right:12px"><input type="checkbox" name="profiles" value="{esc(p["id"])}" '
        f'style="width:auto" {"checked" if p["id"] in track["target_profiles"] else ""}> {esc(p["name"])}</label>'
        for p in catalog.list_profiles())
    category_options = "".join(f'<option value="{c}">{c}</option>' for c in TASK_CATEGORIES)
    follow_options = "".join(f'<option value="{f}">{FOLLOW_UP_LABELS[f]}</option>'
                             for f in FOLLOW_UP_OPTIONS)
    responsibles = "".join(
        f'<li id="resp-{r["id"]}">{esc(r["name"])} &lt;{esc(r["email"])}&gt; ({esc(r["role"])}) '
        f'<button class="danger" hx-post="/responsibles/{r["id"]}/delete" hx-target="#resp-{r["id"]}" '
        f'hx-swap="outerHTML">×</button></li>' for r in track["responsibles"])
    tid = esc(track_id)
    body = f"""<div class="card"><h2>Track settings</h2>
<form class="block" method="post" action="/tracks/{tid}/meta">
<label>Name</label><input name="name" value="{esc(track['name'])}">
<label>Duration (weeks)</label><input name="duration_weeks" type="number" value="{esc(track['duration_weeks'])}">
<label>For roles</label><div>{role_checks}</div><br><button>Save settings</button></form></div>

{_task_modal_card(track_id, rows, category_options, follow_options)}

{_responsibles_card(track_id, responsibles)}"""
    return _page(f"{track['name']}", body)


@app.post("/tracks/{track_id}/meta")
async def track_meta(track_id: str, request: Request):
    form = await request.form()
    catalog.update_track(track_id, str(form["name"]).strip(),
                         int(str(form.get("duration_weeks", "4"))), form.getlist("profiles"))
    return RedirectResponse(f"/tracks/{track_id}", status_code=303)


async def _task_fields(request: Request) -> dict:
    form = await request.form()
    return {
        "title": str(form["title"]).strip(),
        "description": str(form.get("description", "")).strip(),
        "category": str(form.get("category", "admin")),
        "due_date": str(form.get("due_date") or "") or None,
        "follow_up": str(form.get("follow_up", "daily")),
        "est_hours": float(str(form["est_hours"])) if str(form.get("est_hours", "")).strip() else None,
        "link": str(form.get("link", "")).strip(),
        "requires_approval": form.get("requires_approval") is not None,
        "contact_name": str(form.get("contact_name", "")).strip(),
        "contact_note": str(form.get("contact_note", "")).strip(),
    }


@app.post("/tracks/{track_id}/tasks")
async def track_add_task(track_id: str, request: Request):
    fields = await _task_fields(request)
    contact_name, contact_note = fields.pop("contact_name"), fields.pop("contact_note")
    contacts = [{"name": contact_name, "note": contact_note}] if contact_name else []
    catalog.create_task(track_id, contacts=contacts, **fields)
    return RedirectResponse(f"/tracks/{track_id}", status_code=303)


@app.get("/tasks/{task_id}/row", response_class=HTMLResponse)
def task_row(task_id: int):
    return HTMLResponse(_task_row(catalog.load_task(task_id)))


@app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def task_edit(task_id: int):
    return HTMLResponse(_task_edit_row(catalog.load_task(task_id)))


@app.post("/tasks/{task_id}", response_class=HTMLResponse)
async def task_save(task_id: int, request: Request):
    catalog.update_task(task_id, **(await _task_fields(request)))
    return HTMLResponse(_task_row(catalog.load_task(task_id)))


@app.post("/tasks/{task_id}/delete", response_class=HTMLResponse)
def task_delete(task_id: int):
    catalog.delete_task(task_id)
    return HTMLResponse("")


@app.post("/tracks/{track_id}/responsibles")
def track_add_responsible(track_id: str, name: str = Form(...), email: str = Form(...),
                          role: str = Form("people-lead")):
    catalog.add_responsible(track_id, name.strip(), email.strip(), role)
    return RedirectResponse(f"/tracks/{track_id}", status_code=303)


@app.post("/responsibles/{responsible_id}/delete", response_class=HTMLResponse)
def responsible_delete(responsible_id: int):
    catalog.delete_responsible(responsible_id)
    return HTMLResponse("")


# ---------- AI Knowledge base (info the AI uses for suggestions) ----------

def _knowledge_row(item: dict) -> str:
    links = []
    if item["url"]:
        links.append(f'<a href="{esc(item["url"])}">course</a>')
    if item["register_url"]:
        links.append(f'<a href="{esc(item["register_url"])}">register completion</a>')
    return (
        f"<tr id='k-{item['id']}'><td><b>{esc(item['title'])}</b>"
        f"<br><small>{esc(item['notes'])}</small></td>"
        f"<td>{esc(item['provider'])}</td><td>{' · '.join(links) or '—'}</td>"
        f"<td><small>{esc(item['tags'] or 'all')}</small></td>"
        f"<td style='white-space:nowrap'>"
        f"<button hx-get='/knowledge/{item['id']}/edit' hx-target='#k-{item['id']}' "
        f"hx-swap='outerHTML'>Edit</button> "
        f"<button class='danger' hx-post='/knowledge/{item['id']}/delete' "
        f"hx-target='#k-{item['id']}' hx-swap='outerHTML' hx-confirm='Delete?'>"
        f"Delete</button></td></tr>")


def _knowledge_edit_row(item: dict) -> str:
    return f"""<tr id="k-{item['id']}" class="editing"><td colspan="5">
<form hx-post="/knowledge/{item['id']}" hx-target="#k-{item['id']}" hx-swap="outerHTML">
<input name="title" value="{esc(item['title'])}" placeholder="Title" required style="width:40%">
<input name="provider" value="{esc(item['provider'])}" placeholder="Provider" style="width:20%">
<input name="tags" value="{esc(item['tags'])}" placeholder="Tags (aws,ai...)" style="width:20%"><br>
<input name="url" value="{esc(item['url'])}" placeholder="Course URL" style="width:40%">
<input name="register_url" value="{esc(item['register_url'])}" placeholder="Register-completion URL" style="width:40%"><br>
<input name="notes" value="{esc(item['notes'])}" placeholder="Notes" style="width:70%">
<button>Save</button>
<button type="button" class="ghost" hx-get="/knowledge/{item['id']}/row"
 hx-target="#k-{item['id']}" hx-swap="outerHTML">Cancel</button>
</form></td></tr>"""


@app.get("/knowledge", response_class=HTMLResponse)
def knowledge_page():
    from bench.tools.knowledge import list_knowledge

    kinds = {"mandatory_course": "Mandatory courses (everyone, must complete)",
             "certification": "Certifications (matched to profile tags)",
             "course": "Suggested courses"}
    sections = []
    for kind, title in kinds.items():
        rows = "".join(_knowledge_row(item) for item in list_knowledge(kind))
        sections.append(f"<div class='card'><h2>{title}</h2>"
                        f"<table><tr><th>Item</th><th>Provider</th><th>Links</th><th>Tags</th><th></th></tr>"
                        f"{rows}</table></div>")
    kind_options = "".join(f"<option value='{k}'>{k}</option>" for k in kinds)
    add_form = f"""<form class="block" method="post" action="/knowledge">
<label>Type</label><select name="kind">{kind_options}</select>
<label>Title</label><input name="title" required>
<label>Provider</label><input name="provider">
<label>Course URL</label><input name="url">
<label>Where to register completion (URL)</label><input name="register_url">
<label>Tags (csv, matched against the profile: aws,azure,ai,backend...)</label><input name="tags">
<label>Notes</label><input name="notes">
<button>Add</button></form>"""
    head = (f'<div class="card"><div class="card-head">'
            f'<p><small>This grid feeds the AI: mandatory courses apply to everyone; '
            f'certifications and courses are suggested when their tags match the person\'s '
            f'Endava Profile.</small></p>{_modal("new-k", "Add knowledge", "Add knowledge", add_form)}</div></div>')
    return _page("AI Knowledge", head + "".join(sections))


@app.post("/knowledge")
def knowledge_add(kind: str = Form(...), title: str = Form(...), provider: str = Form(""),
                  url: str = Form(""), register_url: str = Form(""), tags: str = Form(""),
                  notes: str = Form("")):
    from bench.tools.knowledge import add_knowledge

    add_knowledge(kind, title.strip(), provider.strip(), url.strip(),
                  register_url.strip(), tags.strip(), notes.strip())
    return RedirectResponse("/knowledge", status_code=303)


@app.get("/knowledge/{item_id}/row", response_class=HTMLResponse)
def knowledge_row(item_id: int):
    from bench.tools.knowledge import get_knowledge

    return HTMLResponse(_knowledge_row(get_knowledge(item_id)))


@app.get("/knowledge/{item_id}/edit", response_class=HTMLResponse)
def knowledge_edit(item_id: int):
    from bench.tools.knowledge import get_knowledge

    return HTMLResponse(_knowledge_edit_row(get_knowledge(item_id)))


@app.post("/knowledge/{item_id}", response_class=HTMLResponse)
def knowledge_save(item_id: int, title: str = Form(...), provider: str = Form(""),
                   url: str = Form(""), register_url: str = Form(""),
                   tags: str = Form(""), notes: str = Form("")):
    from bench.tools.knowledge import get_knowledge, update_knowledge

    update_knowledge(item_id, title=title.strip(), provider=provider.strip(),
                     url=url.strip(), register_url=register_url.strip(),
                     tags=tags.strip(), notes=notes.strip())
    return HTMLResponse(_knowledge_row(get_knowledge(item_id)))


@app.post("/knowledge/{item_id}/delete", response_class=HTMLResponse)
def knowledge_delete(item_id: int):
    from bench.tools.knowledge import delete_knowledge

    delete_knowledge(item_id)
    return HTMLResponse("")


# Backwards-compatible redirect from the old combined page
@app.get("/catalog")
def catalog_redirect():
    return RedirectResponse("/roles", status_code=303)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    from bench.config import require_bench_enabled

    require_bench_enabled()
    uvicorn.run(app, host="127.0.0.1", port=8000)
