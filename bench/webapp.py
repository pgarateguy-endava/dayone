"""Bench Assistant — dev web UI (FastAPI + htmx) over the SQLite catalog.

Views:
- /            responsibles dashboard (everyone on bench, progress, blockers, deadline risk)
- /onboard     assign a person to bench (employee + profile + track)
- /person/...  person cycle: task board with status/evidence, AM/PM check-in, EOD report
- /roles       ABM of roles (inline edit/delete) — context the AI uses for access boundaries
- /tracks      ABM of tracks; /tracks/{id} = task ABM with inline edit/delete + responsibles

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

app = FastAPI(title="Bench Assistant (dev UI)")

_CSS = """
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f5f2; color: #222; }
nav { background: #1f2937; color: #fff; padding: 10px 24px; display: flex; gap: 18px; }
nav a { color: #e5e7eb; text-decoration: none; font-weight: 600; }
main { max-width: 1150px; margin: 24px auto; padding: 0 16px; }
.card { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top; }
.badge { padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.ok { background: #dcfce7; color: #166534; } .warn { background: #fef9c3; color: #854d0e; }
.bad { background: #fee2e2; color: #991b1b; } .info { background: #e0e7ff; color: #3730a3; }
input, select, textarea { padding: 6px; margin: 2px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font: inherit; }
form.block input, form.block select, form.block textarea { width: 100%; margin-bottom: 10px; }
button { background: #1f2937; color: #fff; border: 0; border-radius: 6px; padding: 7px 14px; font-weight: 600; cursor: pointer; }
button.danger { background: #b91c1c; } button.ghost { background: #6b7280; }
h1 { font-size: 22px; } h2 { font-size: 17px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
a { color: #1d4ed8; } small { color: #6b7280; }
tr.editing td { background: #f8fafc; }
dialog { border: 1px solid #ddd; border-radius: 12px; padding: 22px 26px; min-width: 480px; max-width: 640px; }
dialog::backdrop { background: rgba(15, 23, 42, .45); }
dialog h2 { margin-top: 0; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
button.add { border-radius: 999px; font-size: 15px; }
"""


def _modal(modal_id: str, button_label: str, title: str, form_html: str) -> str:
    """A '+' button that opens a native <dialog> modal containing the given form."""
    return f"""<button class="add" onclick="document.getElementById('{modal_id}').showModal()">＋ {button_label}</button>
<dialog id="{modal_id}"><h2>{title}</h2>{form_html}
<button type="button" class="ghost" onclick="document.getElementById('{modal_id}').close()">Cancel</button>
</dialog>"""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html><head><meta charset="utf-8">
<title>{title} · Bench Assistant</title>
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>{_CSS}</style></head><body>
<nav><a href="/">Dashboard</a><a href="/onboard">Onboard to bench</a>
<a href="/roles">Roles</a><a href="/tracks">Tracks</a></nav>
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
    options_p = "".join(f'<option value="{p["id"]}">{p["name"]}</option>'
                        for p in catalog.list_profiles())
    options_t = "".join(f'<option value="{t["id"]}">{t["name"]}</option>'
                        for t in catalog.list_tracks())
    return _page("Onboard to bench", f"""<div class="card"><form class="block" method="post" action="/onboard">
<label>Name</label><input name="employee" required>
<label>Email</label><input name="email" type="email" required>
<label>Role (context for the AI — defines access boundaries)</label><select name="profile">{options_p}</select>
<label>Track (bench plan — tasks, deadlines, follow-up)</label><select name="track">{options_t}</select>
<button>Create bench plan</button></form></div>""")


@app.post("/onboard")
def onboard(employee: str = Form(...), email: str = Form(...),
            profile: str = Form(...), track: str = Form(...)):
    start_bench(employee, email, profile, track)
    return RedirectResponse(f"/person/{email}", status_code=303)


# ---------- Person cycle ----------

def _person_task_row(email: str, task: dict) -> str:
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
    profile = catalog.load_profile(state["profile_id"])
    track = catalog.load_track(state["track_id"])
    verification = verify_progress(state, track)
    plan = generate_bench_plan(state["employee_name"], email, profile, track)

    catalog_tasks = {t["id"]: t for t in track["tasks"]}
    for task in state["tasks"]:
        task["contacts"] = catalog_tasks.get(task["task_id"], {}).get("contacts", [])
    task_rows = "".join(_person_task_row(email, t) for t in state["tasks"])

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
                               f'<p><i>Saved to {path} (simulated Teams delivery).</i></p></div>')


# ---------- Roles ABM ----------

def _role_row(profile: dict) -> str:
    perms = "<br>".join(f"<small><b>{k}:</b> {', '.join(v)}</small>"
                        for k, v in profile["permissions"].items()) or "<small>—</small>"
    approvals = ", ".join(profile["approvals_required"]) or "—"
    return f"""<tr id="role-{profile['id']}">
<td><b>{profile['name']}</b><br><small>{profile['id']}</small></td>
<td>{profile['summary']}</td><td>{perms}</td><td><small>{approvals}</small></td>
<td style="white-space:nowrap">
<button hx-get="/roles/{profile['id']}/edit" hx-target="#role-{profile['id']}" hx-swap="outerHTML">Edit</button>
<button class="danger" hx-post="/roles/{profile['id']}/delete" hx-target="#role-{profile['id']}"
 hx-swap="outerHTML" hx-confirm="Delete role {profile['id']}?">Delete</button></td></tr>"""


def _role_edit_row(profile: dict) -> str:
    perms_text = "&#10;".join(f"{k}: {v}" for k, values in profile["permissions"].items()
                              for v in values)
    approvals_text = "&#10;".join(profile["approvals_required"])
    return f"""<tr id="role-{profile['id']}" class="editing">
<td colspan="5"><form hx-post="/roles/{profile['id']}" hx-target="#role-{profile['id']}" hx-swap="outerHTML">
<b>{profile['id']}</b><br>
<input name="name" value="{profile['name']}" placeholder="Name" style="width:30%">
<input name="summary" value="{profile['summary']}" placeholder="Summary" style="width:60%"><br>
<textarea name="permissions" rows="4" placeholder="aws: staging-read" style="width:45%">{perms_text}</textarea>
<textarea name="approvals" rows="4" placeholder="prod-write" style="width:45%">{approvals_text}</textarea><br>
<button>Save</button>
<button type="button" class="ghost" hx-get="/roles/{profile['id']}/row"
 hx-target="#role-{profile['id']}" hx-swap="outerHTML">Cancel</button>
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
                                        f'<br><span class="badge bad">{exc}</span></td></tr>'))


# ---------- Tracks ABM ----------

@app.get("/tracks", response_class=HTMLResponse)
def tracks_list():
    rows = []
    for track in catalog.list_tracks():
        rows.append(f"""<tr id="track-{track['id']}">
<td><a href="/tracks/{track['id']}"><b>{track['name']}</b></a><br><small>{track['id']}</small></td>
<td>{track['duration_weeks']} weeks</td>
<td>{', '.join(track['target_profiles']) or '—'}</td>
<td>{len(track['tasks'])} tasks</td>
<td><button class="danger" hx-post="/tracks/{track['id']}/delete" hx-target="#track-{track['id']}"
 hx-swap="outerHTML" hx-confirm="Delete track {track['id']} and its tasks?">Delete</button></td></tr>""")
    role_checks = "".join(
        f'<label style="margin-right:12px"><input type="checkbox" name="profiles" value="{p["id"]}" '
        f'style="width:auto"> {p["name"]}</label>' for p in catalog.list_profiles())
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
        return HTMLResponse(f'<tr id="track-{track_id}"><td colspan="5">'
                            f'<span class="badge bad">{exc}</span></td></tr>')


def _task_row(task: dict) -> str:
    contact = task["contacts"][0] if task["contacts"] else None
    contact_html = (f'<br><small>👤 {contact["name"]}'
                    f'{" — " + contact["note"] if contact["note"] else ""}</small>') if contact else ""
    return f"""<tr id="task-{task['id']}">
<td><b>{task['title']}</b><br><small>{task['description']}</small>{contact_html}</td>
<td>{task['category']}</td><td>{task['due_date'] or '—'}</td>
<td>{FOLLOW_UP_LABELS.get(task['follow_up'], task['follow_up'])}</td>
<td>{task['est_hours'] or '—'}</td><td>{'yes' if task['requires_approval'] else 'no'}</td>
<td style="white-space:nowrap">
<button hx-get="/tasks/{task['id']}/edit" hx-target="#task-{task['id']}" hx-swap="outerHTML">Edit</button>
<button class="danger" hx-post="/tasks/{task['id']}/delete" hx-target="#task-{task['id']}"
 hx-swap="outerHTML" hx-confirm="Delete task '{task['title']}'?">Delete</button></td></tr>"""


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
<input name="title" value="{task['title']}" placeholder="Task" style="width:32%" required>
<input name="description" value="{task['description']}" placeholder="Description" style="width:55%"><br>
<select name="category">{category_options}</select>
<input name="due_date" type="date" value="{task['due_date'] or ''}">
<select name="follow_up">{follow_options}</select>
<input name="est_hours" type="number" step="0.5" value="{task['est_hours'] or ''}" placeholder="h" style="width:70px">
<input name="link" value="{task['link']}" placeholder="Link" style="width:20%">
<label style="white-space:nowrap"><input type="checkbox" name="requires_approval" style="width:auto"
 {'checked' if task['requires_approval'] else ''}> needs approval</label><br>
<input name="contact_name" value="{contact['name']}" placeholder="Contact (optional)">
<input name="contact_note" value="{contact['note']}" placeholder="Why this contact" style="width:40%">
<button>Save</button>
<button type="button" class="ghost" hx-get="/tasks/{task['id']}/row"
 hx-target="#task-{task['id']}" hx-swap="outerHTML">Cancel</button>
</form></td></tr>"""


def _task_modal_card(track_id: str, rows: str, category_options: str, follow_options: str) -> str:
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
        f'<label style="margin-right:12px"><input type="checkbox" name="profiles" value="{p["id"]}" '
        f'style="width:auto" {"checked" if p["id"] in track["target_profiles"] else ""}> {p["name"]}</label>'
        for p in catalog.list_profiles())
    category_options = "".join(f'<option value="{c}">{c}</option>' for c in TASK_CATEGORIES)
    follow_options = "".join(f'<option value="{f}">{FOLLOW_UP_LABELS[f]}</option>'
                             for f in FOLLOW_UP_OPTIONS)
    responsibles = "".join(
        f'<li id="resp-{r["id"]}">{r["name"]} &lt;{r["email"]}&gt; ({r["role"]}) '
        f'<button class="danger" hx-post="/responsibles/{r["id"]}/delete" hx-target="#resp-{r["id"]}" '
        f'hx-swap="outerHTML">×</button></li>' for r in track["responsibles"])
    body = f"""<div class="card"><h2>Track settings</h2>
<form class="block" method="post" action="/tracks/{track_id}/meta">
<label>Name</label><input name="name" value="{track['name']}">
<label>Duration (weeks)</label><input name="duration_weeks" type="number" value="{track['duration_weeks']}">
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


# Backwards-compatible redirect from the old combined page
@app.get("/catalog")
def catalog_redirect():
    return RedirectResponse("/roles", status_code=303)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    from bench.config import require_bench_enabled

    require_bench_enabled()
    uvicorn.run(app, host="127.0.0.1", port=8000)
