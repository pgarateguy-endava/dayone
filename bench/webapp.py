"""Bench Assistant — dev web UI (FastAPI + htmx).

Follows docs/BACKOFFICE_SPEC.md direction (FastAPI option) and mirrors the AWS
accelerator's chatapp stack, so this UI can evolve into the real backoffice.

Views:
- /            responsibles dashboard (everyone on bench, progress, blockers, deadline risk)
- /onboard     assign a person to bench (employee + profile + track)
- /person/...  person cycle: plan, AM/PM check-in, EOD report
- /catalog     roles (profiles) and tracks, their relations, and a YAML editor

Run:
    BENCH_ENABLED=1 uv run --group ui uvicorn bench.webapp:app --reload
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

try:
    from fastapi import FastAPI, Form, Request
    from fastapi.responses import HTMLResponse, RedirectResponse
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The web UI needs FastAPI. Install with: uv sync --group ui"
    ) from exc

from agent.config import PROFILES_DIR
from agent.tools.load_profile import load_profile
from bench.config import TRACKS_DIR, bench_enabled
from bench.graph import build_graph
from bench.tools.eod_report import build_eod_report, save_eod_report
from bench.tools.generate_bench_plan import generate_bench_plan
from bench.tools.load_track import load_track
from bench.tools.state import list_bench_people, load_bench_state, start_bench
from bench.tools.verify_goals import verify_daily_goals

app = FastAPI(title="Bench Assistant (dev UI)")

_CSS = """
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f5f2; color: #222; }
nav { background: #1f2937; color: #fff; padding: 10px 24px; display: flex; gap: 18px; }
nav a { color: #e5e7eb; text-decoration: none; font-weight: 600; }
main { max-width: 1000px; margin: 24px auto; padding: 0 16px; }
.card { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; }
.badge { padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.ok { background: #dcfce7; color: #166534; } .warn { background: #fef9c3; color: #854d0e; }
.bad { background: #fee2e2; color: #991b1b; }
input, select, textarea { width: 100%; padding: 8px; margin: 4px 0 12px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
button { background: #1f2937; color: #fff; border: 0; border-radius: 6px; padding: 9px 18px; font-weight: 600; cursor: pointer; }
h1 { font-size: 22px; } h2 { font-size: 17px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
a { color: #1d4ed8; }
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
    return await call_next(request)


def _badge(verification: dict) -> str:
    rate = verification["completion_rate"]
    cls = "ok" if rate >= 0.99 else ("warn" if rate > 0 else "bad")
    return f'<span class="badge {cls}">{verification["goals_met"]}/{verification["goals_total"]} goals</span>'


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


# ---------- Dashboard (responsibles view) ----------

@app.get("/", response_class=HTMLResponse)
def dashboard():
    rows = []
    for person in list_bench_people():
        state = load_bench_state(person["email"])
        track = load_track(person["track_id"])
        verification = verify_daily_goals(state, track)
        blockers = f'<span class="badge bad">{len(verification["blockers"])} blocker(s)</span>' \
            if verification["blockers"] else ""
        rows.append(
            f'<tr><td><a href="/person/{person["email"]}">{person["name"]}</a></td>'
            f'<td>{person["profile_id"]}</td><td>{person["track_id"]}</td>'
            f'<td>{_badge(verification)} {blockers}</td><td>{_deadline_badge(verification)}</td>'
            f'<td>AM {"✓" if verification["checked_in_am"] else "—"} / '
            f'PM {"✓" if verification["checked_in_pm"] else "—"}</td></tr>'
        )
    table = ("<table><tr><th>Person</th><th>Profile</th><th>Track</th><th>Today</th>"
             "<th>Deadlines</th><th>Check-ins</th></tr>" + "".join(rows) + "</table>") \
        if rows else "<p>Nobody on bench yet. <a href='/onboard'>Onboard someone</a>.</p>"
    return _page("Bench dashboard", f'<div class="card">{table}</div>')


# ---------- Onboard (backoffice create) ----------

@app.get("/onboard", response_class=HTMLResponse)
def onboard_form():
    profiles = sorted(p.stem for p in Path(PROFILES_DIR).glob("*.yaml"))
    tracks = sorted(t.stem for t in Path(TRACKS_DIR).glob("*.yaml"))
    options_p = "".join(f'<option value="{p}">{p}</option>' for p in profiles)
    options_t = "".join(f'<option value="{t}">{t}</option>' for t in tracks)
    return _page("Onboard to bench", f"""<div class="card"><form method="post" action="/onboard">
<label>Name</label><input name="employee" required>
<label>Email</label><input name="email" type="email" required>
<label>Profile (role — defines access)</label><select name="profile">{options_p}</select>
<label>Track (bench plan — courses, goals, deadlines)</label><select name="track">{options_t}</select>
<button>Create bench plan</button></form></div>""")


@app.post("/onboard")
def onboard(employee: str = Form(...), email: str = Form(...),
            profile: str = Form(...), track: str = Form(...)):
    start_bench(employee, email, profile, track)
    return RedirectResponse(f"/person/{email}", status_code=303)


# ---------- Person cycle ----------

@app.get("/person/{email}", response_class=HTMLResponse)
def person_view(email: str):
    state = load_bench_state(email)
    profile = load_profile(state["profile_id"])
    track = load_track(state["track_id"])
    verification = verify_daily_goals(state, track)
    plan = generate_bench_plan(state["employee_name"], email, profile, track)

    goal_inputs = "".join(
        f'<label><input type="checkbox" name="done" value="{i}" style="width:auto"> {g}</label>'
        f'<input name="evidence_{i}" placeholder="Evidence (course %, commit URL, profile diff)">'
        for i, g in enumerate(track.get("daily_goals", []), start=1)
    )
    body = f"""
<div class="card"><b>Today:</b> {_badge(verification)} {_deadline_badge(verification)}
&nbsp; <a href="/person/{email}/report">Generate EOD report</a></div>
<div class="cols">
<div class="card"><h2>AM check-in — plan the day</h2>
<form method="post" action="/person/{email}/checkin"><input type="hidden" name="period" value="am">
<label>What will you work on today?</label><textarea name="planned" rows="3"></textarea>
<label>Blockers</label><input name="blockers"><button>Check in (AM)</button></form></div>
<div class="card"><h2>PM check-in — report completions</h2>
<form method="post" action="/person/{email}/checkin"><input type="hidden" name="period" value="pm">
{goal_inputs}<label>Blockers</label><input name="blockers"><button>Check in (PM)</button></form></div>
</div>
<div class="card"><h2>Bench plan</h2>{_md(plan, "plan")}</div>"""
    return _page(state["employee_name"], body)


@app.post("/person/{email}/checkin")
async def person_checkin(email: str, request: Request):
    form = await request.form()
    period = form["period"]
    done = [{"goal": int(i), "evidence": str(form.get(f"evidence_{i}", ""))}
            for i in form.getlist("done")]
    planned = [p for p in [str(form.get("planned", "")).strip()] if p]
    # The check-in runs through the LangGraph daily cycle (records, verifies, reports on PM).
    build_graph().invoke({
        "employee_email": email, "period": period,
        "done_goals": done, "planned": planned, "blockers": str(form.get("blockers", "")),
    })
    return RedirectResponse(f"/person/{email}", status_code=303)


@app.get("/person/{email}/report", response_class=HTMLResponse)
def person_report(email: str):
    state = load_bench_state(email)
    track = load_track(state["track_id"])
    verification = verify_daily_goals(state, track)
    report = build_eod_report(state, track, verification)
    path = save_eod_report(report, email, verification["date"])
    return _page("EOD report", f'<div class="card">{_md(report, "report")}'
                               f'<p><i>Saved to {path} (simulated Teams delivery).</i></p></div>')


# ---------- Catalog: roles, tracks and their relations ----------

def _yaml_files(kind: str) -> Path:
    return Path(PROFILES_DIR) if kind == "profile" else Path(TRACKS_DIR)


@app.get("/catalog", response_class=HTMLResponse)
def catalog():
    tracks = {t.stem: yaml.safe_load(t.read_text(encoding="utf-8"))
              for t in sorted(Path(TRACKS_DIR).glob("*.yaml"))}
    cards = []
    for p in sorted(Path(PROFILES_DIR).glob("*.yaml")):
        profile = yaml.safe_load(p.read_text(encoding="utf-8"))
        related = [tid for tid, t in tracks.items()
                   if profile["id"] in t.get("target_profiles", [])]
        aws = ", ".join(profile.get("permissions", {}).get("aws", [])) or "—"
        approvals = ", ".join(profile.get("approvals_required", [])) or "—"
        links = ", ".join(f'<a href="/catalog/track/{t}">{t}</a>' for t in related) or "none"
        cards.append(f"""<div class="card"><h2>{profile.get('name')} <small>({profile['id']})</small></h2>
<p>{profile.get('summary', '')}</p>
<p><b>AWS access:</b> {aws}<br><b>Needs approval:</b> {approvals}<br>
<b>Bench tracks for this role:</b> {links}</p>
<a href="/catalog/profile/{profile['id']}">Edit role YAML</a></div>""")
    for tid, t in tracks.items():
        goals = "".join(f"<li>{g}</li>" for g in t.get("daily_goals", []))
        courses = ", ".join(c["name"] for c in t.get("mandatory_courses", []))
        cards.append(f"""<div class="card"><h2>{t.get('name')} <small>({tid})</small></h2>
<p><b>For roles:</b> {', '.join(t.get('target_profiles', []))} · <b>{t.get('duration_weeks')} weeks</b><br>
<b>Courses:</b> {courses}</p><b>Daily goals (verified at PM check-in):</b><ul>{goals}</ul>
<a href="/catalog/track/{tid}">Edit track YAML</a></div>""")
    return _page("Catalog — roles & tracks", "".join(cards))


@app.get("/catalog/{kind}/{item_id}", response_class=HTMLResponse)
def catalog_edit(kind: str, item_id: str, error: str = ""):
    path = _yaml_files(kind) / f"{item_id}.yaml"
    content = path.read_text(encoding="utf-8")
    err = f'<p class="badge bad">{error}</p>' if error else ""
    return _page(f"Edit {kind}: {item_id}", f"""<div class="card">{err}
<form method="post" action="/catalog/{kind}/{item_id}">
<textarea name="content" rows="28" style="font-family:monospace">{content}</textarea>
<button>Validate & save</button></form>
<p><i>Saved to versioned YAML — commit the change in git to make it official.</i></p></div>""")


@app.post("/catalog/{kind}/{item_id}")
def catalog_save(kind: str, item_id: str, content: str = Form(...)):
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return RedirectResponse(f"/catalog/{kind}/{item_id}?error=Invalid YAML: {exc}"[:500],
                                status_code=303)
    (_yaml_files(kind) / f"{item_id}.yaml").write_text(content, encoding="utf-8")
    return RedirectResponse("/catalog", status_code=303)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    from bench.config import require_bench_enabled

    require_bench_enabled()
    uvicorn.run(app, host="127.0.0.1", port=8000)
