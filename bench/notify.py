"""Proactive notifications engine (journey B6 — the bot writes first).

The SERVICE decides and records what to say (this module, deterministic, from the DB);
the BOT polls /api/v1/notifications/pending and delivers via Teams proactive messages.
Every contact is logged in `notifications` — the daily-update trail Pedro asked for.

Rules (evaluated by the scheduler in webapp startup, and testable directly):
- pre_bench + start date within 7 days  -> 'pre_bench_greeting' (once): heads-up + update profile.
- active + start date reached           -> 'kickoff' (once): mandatory courses, suggestions
                                           from their Endava Profile, and "what's your plan?".
- active >= 7 days                      -> 'progress_check' (weekly): verified progress vs plan.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from bench.db import connect
from bench.tools.catalog import load_track
from bench.tools.knowledge import suggest_for_profile
from bench.tools.state import list_bench_people, load_bench_state
from bench.tools.verify_goals import verify_progress


def save_conversation_ref(email: str, conversation_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO conversation_refs (email, conversation_id, updated_at) "
            "VALUES (?, ?, ?)", (email, conversation_id, datetime.now(timezone.utc).isoformat()))


def _already_sent(conn, email: str, kind: str, since_days: int | None = None) -> bool:
    query = "SELECT COUNT(*) FROM notifications WHERE email = ? AND kind = ?"
    params: list = [email, kind]
    if since_days is not None:
        query += " AND created_at >= date('now', ?)"
        params.append(f"-{since_days} days")
    return conn.execute(query, params).fetchone()[0] > 0


def _delivered(conn, email: str, kind: str) -> bool:
    return conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE email = ? AND kind = ? "
        "AND delivered_at IS NOT NULL", (email, kind)).fetchone()[0] > 0


def _queue(conn, email: str, kind: str, message: str) -> None:
    conn.execute(
        "INSERT INTO notifications (email, kind, message, created_at) VALUES (?, ?, ?, ?)",
        (email, kind, message, datetime.now(timezone.utc).isoformat()))


def _fmt_items(items: list[dict]) -> str:
    lines = []
    for item in items:
        line = f"- **{item['title']}**" + (f" ({item['provider']})" if item["provider"] else "")
        if item["url"]:
            line += f" — {item['url']}"
        if item["register_url"]:
            line += f"\n  Al terminarlo, registralo acá: {item['register_url']}"
        lines.append(line)
    return "\n".join(lines) or "- (pendiente de carga)"


def _kickoff_message(state: dict) -> str:
    suggestions = suggest_for_profile(state.get("profile_text", ""))
    return (
        f"¡Hola {state['employee_name'].split()[0]}! 👋 Hoy arranca tu bench y soy tu coach.\n\n"
        f"**Cursos obligatorios (sí o sí):**\n{_fmt_items(suggestions['mandatory'])}\n\n"
        f"**Certificaciones sugeridas según tu perfil:**\n{_fmt_items(suggestions['certifications'])}\n\n"
        f"**Cursos recomendados:**\n{_fmt_items(suggestions['courses'])}\n\n"
        "¿Cuál es tu plan? Contame por dónde querés empezar y lo registramos juntos."
    )


def _progress_message(state: dict) -> str:
    verification = verify_progress(state, load_track(state["track_id"]))
    return (
        f"¡Hola {state['employee_name'].split()[0]}! Ya llevás una semana o más en bench. "
        f"Según el plan, vas {verification['tasks_done']}/{verification['tasks_total']} tareas "
        f"({int(verification['completion_rate'] * 100)}%). "
        "¿Cómo vienen los avances? Contame qué completaste (con evidencia) y qué te está trabando."
    )


def generate_due_notifications(today: str | None = None) -> int:
    """Evaluate the rules for everyone and queue what's due. Returns queued count."""
    today_d = date.fromisoformat(today) if today else date.today()
    queued = 0
    from bench.tools.state import computed_status

    with connect() as conn:
        for person in list_bench_people():
            email = person["email"]
            start = person["bench_start_date"]
            status = computed_status(start, today_d.isoformat())
            start_d = date.fromisoformat(start) if start else None
            if status == "pre_bench" and start_d and 0 < (start_d - today_d).days <= 7:
                if not _already_sent(conn, email, "pre_bench_greeting"):
                    _queue(conn, email, "pre_bench_greeting",
                           f"¡Hola {person['name'].split()[0]}! 👋 En {(start_d - today_d).days} "
                           f"día(s) entrás a bench (el {start}). Primer paso sugerido: empezá a "
                           "actualizar tu Endava Profile así arrancamos con tu plan al día. "
                           "Cuando quieras te cuento qué te va a tocar.")
                    queued += 1
            if status == "active" and (start_d is None or start_d <= today_d):
                if not _already_sent(conn, email, "kickoff"):
                    _queue(conn, email, "kickoff", _kickoff_message(load_bench_state(email)))
                    queued += 1
                elif (start_d and (today_d - start_d).days >= 7
                      and _delivered(conn, email, "kickoff")  # follow-up only after kickoff landed
                      and not _already_sent(conn, email, "progress_check", since_days=7)):
                    _queue(conn, email, "progress_check",
                           _progress_message(load_bench_state(email)))
                    queued += 1
    return queued


def pending_notifications() -> list[dict]:
    """Undelivered notifications joined with their Teams conversation ref."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT n.id, n.email, n.kind, n.message, c.conversation_id
               FROM notifications n LEFT JOIN conversation_refs c ON c.email = n.email
               WHERE n.delivered_at IS NULL ORDER BY n.id""").fetchall()
    return [dict(r) for r in rows]


def mark_delivered(notification_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE notifications SET delivered_at = ? WHERE id = ?",
                     (datetime.now(timezone.utc).isoformat(), notification_id))


def notification_log(email: str | None = None) -> list[dict]:
    query = "SELECT * FROM notifications" + (" WHERE email = ?" if email else "") + " ORDER BY id DESC"
    with connect() as conn:
        return [dict(r) for r in conn.execute(query, (email,) if email else ()).fetchall()]
