"""Bench Assistant — dev web UI (FastAPI + htmx) over the SQLite catalog.

Views:
- /            responsibles dashboard (everyone on bench, progress, blockers, deadline risk)
- /onboard     assign a person to bench (employee + profile + track)
- /person/...  person cycle: task board with status/evidence, AM/PM check-in, EOD report
- /catalog     roles and tracks from the DB: relations, add tasks, add roles

Run:
    BENCH_ENABLED=1 uv run --group ui uvicorn bench.webapp:app --reload
"""
from __future__ import annotations

import json

try:
    from fastapi import FastAPI, Form, Request
    from fastapi.responses import HTMLResponse, RedirectResponse
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The web UI needs FastAPI. Install with: uv sync --group ui") from exc

from bench.config import bench_enabled
from bench.db import FOLLOW_UP_OPTIONS, TASK_CATEGORIES, TASK_STATUSES
from bench.graph import build_graph
from bench.seed import seed_if_empty
from bench.tools.catalog import (
    create_task,
    list_profiles,
    list_tracks,
    load_profile,
    load_track,
    upsert_profile,
)
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.state import (
    list_bench_people,
    load_bench_state,
    start_bench,
    update_task_status,
)
from bench.tools.verify_goals import FOLLOW_UP_LABELS, verify_progress

app = FastAPI(title="Bench Assistant (dev UI)")

_CSS = """
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f5f2; color: #222; }
nav { background: #1f2937; color: #fff; padding: 10px 24px; display: flex; gap: 18px; }
nav a { color: #e5e7eb; text-decoration: none; font-weight: 600; }
main { max-width: 1100px; margin: 24px auto; padding: 0 16px; }
.card { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top; }
.badge { padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.ok { background: #dcfce7; color: #166534; } .warn { background: #fef9c3; color: #854d0e; }
.bad { background: #fee2e2; color: #991b1b; } .info { background: #e0e7ff; color: #3730a3; }
input, select, textarea { padding: 7px; margin: 3px 0 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
form.block input, form.block select, form.block textarea { width: 100%; }
button { background: #1f2937; color: #fff; border: 0; border-radius: 6px; padding: 8px 16px; font-weight: 600; cursor: pointer; }
h1 { font-size: 22px; } h2 { font-size: 17px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
a { color: #1d4ed8; } small { color: #6b7280; }
"""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html><head><meta charset="utf-8">
<title>{title} · Bench Assistant</title>
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>{_CSS}</style></head><body>
<nav><a href="/">Dashboard</a><a href="/onboard">Onboard to bench</a><a href="/catalog">Catalog</a></nav>
<main><h1>{title}</h1>{body}</main></body></html>""")


@app.middleware("http")
async def _flag_gate(request: Request, call_next):
    if not bench_enabled():
        return HTMLResponse("Bench domain is disabled. Set BENCH_ENABLED=1.", status_code=403)
    seed_if_empty()
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


# ---------- Dashboard (responsibles view) ----------

@app.get("/", response_class=HTMLResponse)
def dashboard():
    rows = []
    for person in list_bench_people():
        state = load_bench_state(person["email"])
        track = load_track(person["track_id"])
        verification = verify_progress(state, track)
        blockers = f'<span class="badge bad">{len(verification["blockers"])} blocker(s)</span>' \
            if verification["blockers"] else ""
        rows.append(
            f'<tr><td><a href="/person/{person["email"]}">{person["name"]}</a></td>'
            f'<td>{person["profile_id"]}</td><td>{person["track_id"]}</td>'
            f'<td>{_progress_badge(verification)} {blockers}</td>'
            f'<td>{_deadline_badge(verification)}</td>'
            f'<td>AM {"✓" if verification["checked_in_am"] else "—"} / '
            f'PM {"✓" if verification["checked_in_pm"] else "—"}</td></tr>')
    table = ("<table><tr><th>Person</th><th>Profile</th><th>Track</th><th>Progress</th>"
             "<th>Deadlines</th><th>Check-ins</th></tr>" + "".join(rows) + "</table>") \
        if rows else "<p>Nobody on bench yet. <a href='/onboard'>Onboard someone</a>.</p>"
    return _page("Bench dashboard", f'<div class="card">{table}</div>')


# ---------- Onboard ----------

@app.get("/onboard", response_class=HTMLResponse)
def onboard_form():
    options_p = "".join(f'<option value="{p["id"]}">{p["name"]}</option>' for p in list_profiles())
    options_t = "".join(f'<option value="{t["id"]}">{t["name"]}</option>' for t in list_tracks())
    return _page("Onboard to bench", f"""<div class="card"><form class="block" method="post" action="/onboard">
<label>Name</label><input name="employee" required>
<label>Email</label><input name="email" type="email" required>
<label>Profile (role — defines access)</label><select name="profile">{options_p}</select>
<label>Track (bench plan — tasks, deadlines, follow-up)</label><select name="track">{options_t}</select>
<button>Create bench plan</button></form></div>""")


@app.post("/onboard")
def onboard(employee: str = Form(...), email: str = Form(...),
            profile: str = Form(...), track: str = Form(...)):
    start_bench(employee, email, profile, track)
    return RedirectResponse(f"/person/{email}", status_code=303)


# ---------- Person cycle ----------

def _task_row(email: str, task: dict) -> str:
    status_options = "".join(
        f'<option value="{s}" {"selected" if s == task["status"] else ""}>{s}</option>'
        for s in TASK_STATUSES)
    due = f'<br><small>due {task["due_date"]}</small>' if task["due_date"] else ""
    contacts = "".join(f'<br><small>👤 {c["name"]}{" — " + c["note"] if c["note"] else ""}</small>'
                       for c in task.get("contacts", []))
    evidence_hint = "required" if task["evidence_required"] else "optional"
    return f"""<tr><td><b>{task['title']}</b><br><small>{task['description']}</small>{contacts}</td>
<td>{task['category']}{due}</td>
<td><small>{FOLLOW_UP_LABELS.get(task['follow_up'], task['follow_up'])}</small></td>
<td>{_status_badge(task['status'])}</td>
<td><form method="post" action="/person/{email}/task/{task['task_id']}">
<select name="status">{status_options}</select>
<input name="evidence" placeholder="Evidence ({evidence_hint})" value="{task['evidence']}">
<button>Update</button></form></td></tr>"""


@app.get("/person/{email}", response_class=HTMLResponse)
def person_view(email: str):
    state = load_bench_state(email)
    profile = load_profile(state["profile_id"])
    track = load_track(state["track_id"])
    verification = verify_progress(state, track)
    plan = generate_bench_plan(state["employee_name"], email, profile, track)

    # merge catalog contacts into the person's task rows
    catalog_tasks = {t["id"]: t for t in track["tasks"]}
    for task in state["tasks"]:
        task["contacts"] = catalog_tasks.get(task["task_id"], {}).get("contacts", [])
    task_rows = "".join(_task_row(email, t) for t in state["tasks"])

    body = f"""
<div class="card"><b>Today:</b> {_progress_badge(verification)} {_deadline_badge(verification)}
&nbsp; <a href="/person/{email}/report">Generate EOD report</a></div>
<div class="card"><h2>My tasks</h2>
<table><tr><th>Task</th><th>Category</th><th>Follow-up</th><th>Status</th><th>Update</th></tr>
{task_rows}</table></div>
<div class="cols">
<div class="card"><h2>AM check-in — plan the day</h2>
<form class="block" method="post" action="/person/{email}/checkin"><input type="hidden" name="period" value="am">
<label>What will you work on today?</label><textarea name="planned" rows="2"></textarea>
<label>Blockers</label><input name="blockers"><button>Check in (AM)</button></form></div>
<div class="card"><h2>PM check-in — close the day</h2>
<p><small>Update your tasks above first; the PM check-in verifies and reports.</small></p>
<form class="block" method="post" action="/person/{email}/checkin"><input type="hidden" name="period" value="pm">
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
    # The check-in runs through the LangGraph daily cycle (verifies, reports on PM).
    build_graph().invoke({
        "employee_email": email, "period": str(form["period"]),
        "task_updates": [], "planned": planned, "blockers": str(form.get("blockers", "")),
    })
    return RedirectResponse(f"/person/{email}", status_code=303)


@app.get("/person/{email}/report", response_class=HTMLResponse)
def person_report(email: str):
    state = load_bench_state(email)
    track = load_track(state["track_id"])
    verification = verify_progress(state, track)
    report = build_eod_report(state, track, verification)
    path = save_eod_report(report, email, verification["date"])
    return _page("EOD report", f'<div class="card">{_md(report, "report")}'
                               f'<p><i>Saved to {path} (simulated Teams delivery).</i></p></div>')


# ---------- Catalog: roles, tracks and their relations (DB-backed) ----------

@app.get("/catalog", response_class=HTMLResponse)
def catalog():
    tracks = list_tracks()
    cards = []
    for profile in list_profiles():
        related = [t["id"] for t in tracks if profile["id"] in t["target_profiles"]]
        aws = ", ".join(profile["permissions"].get("aws", [])) or "—"
        approvals = ", ".join(profile["approvals_required"]) or "—"
        cards.append(f"""<div class="card"><h2>{profile['name']} <small>({profile['id']})</small></h2>
<p>{profile['summary']}</p>
<p><b>AWS access:</b> {aws}<br><b>Needs approval:</b> {approvals}<br>
<b>Bench tracks for this role:</b> {', '.join(related) or 'none'}</p></div>""")

    for track in tracks:
        rows = "".join(
            f"<tr><td><b>{t['title']}</b><br><small>{t['description']}</small>"
            + "".join(f"<br><small>👤 {c['name']}{' — ' + c['note'] if c['note'] else ''}</small>"
                      for c in t["contacts"])
            + f"</td><td>{t['category']}</td><td>{t['due_date'] or '—'}</td>"
            f"<td>{FOLLOW_UP_LABELS.get(t['follow_up'], t['follow_up'])}</td>"
            f"<td>{t['est_hours'] or '—'}</td>"
            f"<td>{'yes' if t['requires_approval'] else 'no'}</td></tr>"
            for t in track["tasks"])
        category_options = "".join(f'<option value="{c}">{c}</option>' for c in TASK_CATEGORIES)
        follow_options = "".join(
            f'<option value="{f}">{FOLLOW_UP_LABELS[f]}</option>' for f in FOLLOW_UP_OPTIONS)
        cards.append(f"""<div class="card">
<h2>{track['name']} <small>({track['id']}, {track['duration_weeks']} weeks,
for: {', '.join(track['target_profiles'])})</small></h2>
<table><tr><th>Task</th><th>Category</th><th>Deadline</th><th>Follow-up</th><th>Est. h</th><th>Approval</th></tr>
{rows}</table>
<h2>Add task</h2>
<form method="post" action="/catalog/track/{track['id']}/task">
<input name="title" placeholder="Task" required style="width:30%">
<input name="description" placeholder="Description" style="width:40%">
<select name="category">{category_options}</select>
<input name="due_date" type="date">
<select name="follow_up">{follow_options}</select>
<input name="est_hours" type="number" step="0.5" placeholder="h" style="width:60px">
<input name="contact_name" placeholder="Contact (optional)">
<input name="contact_note" placeholder="Why this contact">
<label style="white-space:nowrap"><input type="checkbox" name="requires_approval" style="width:auto"> needs approval</label>
<button>Add</button></form></div>""")

    cards.append("""<div class="card"><h2>Add role</h2>
<form class="block" method="post" action="/catalog/profile">
<label>Id (e.g. senior-qa)</label><input name="profile_id" required>
<label>Name</label><input name="name" required>
<label>Summary</label><input name="summary">
<label>Permissions (one per line, "kind: value" — kinds: aws, ci_cd, repositories)</label>
<textarea name="permissions" rows="4" placeholder="aws: staging-read&#10;ci_cd: view-build-logs"></textarea>
<label>Actions needing approval (one per line)</label>
<textarea name="approvals" rows="2" placeholder="prod-write"></textarea>
<button>Save role</button></form></div>""")
    return _page("Catalog — roles & tracks", "".join(cards))


@app.post("/catalog/track/{track_id}/task")
async def catalog_add_task(track_id: str, request: Request):
    form = await request.form()
    contacts = []
    if str(form.get("contact_name", "")).strip():
        contacts.append({"name": str(form["contact_name"]).strip(),
                         "note": str(form.get("contact_note", "")).strip()})
    create_task(
        track_id,
        title=str(form["title"]),
        description=str(form.get("description", "")),
        category=str(form.get("category", "admin")),
        due_date=str(form.get("due_date")) or None,
        follow_up=str(form.get("follow_up", "daily")),
        est_hours=float(form["est_hours"]) if str(form.get("est_hours", "")).strip() else None,
        requires_approval=form.get("requires_approval") is not None,
        contacts=contacts,
    )
    return RedirectResponse("/catalog", status_code=303)


@app.post("/catalog/profile")
def catalog_add_profile(profile_id: str = Form(...), name: str = Form(...),
                        summary: str = Form(""), permissions: str = Form(""),
                        approvals: str = Form("")):
    permission_rows = []
    for line in permissions.splitlines():
        kind, _, value = line.partition(":")
        if kind.strip() and value.strip():
            permission_rows.append((kind.strip(), value.strip()))
    approval_rows = [line.strip() for line in approvals.splitlines() if line.strip()]
    upsert_profile(profile_id.strip(), name.strip(), summary.strip(),
                   permission_rows, approval_rows)
    return RedirectResponse("/catalog", status_code=303)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    from bench.config import require_bench_enabled

    require_bench_enabled()
    uvicorn.run(app, host="127.0.0.1", port=8000)
