"""End-of-day report for the responsibles. (Generation + Write tool)

MVP: writes Markdown to .local-progress/reports/. Production: Teams webhook/Graph API.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bench.config import REPORTS_DIR
from bench.db import connect, normalize_email
from bench.tools.audit import append_audit
from bench.tools.verify_goals import FOLLOW_UP_LABELS

_LEVEL_LABEL = {"overdue": "OVERDUE", "at_risk": "AT RISK", "ok": "ok", "done": "done"}


def build_eod_report(
    state: dict[str, Any],
    track: dict[str, Any],
    verification: dict[str, Any],
    summary: str = "",
) -> str:
    """Render the EOD report Markdown from a verification result."""
    followed = []
    for item in verification["follow_up_today"]:
        mark = "x" if item["touched_today"] else " "
        extra = f" — evidence: {item['evidence']}" if item["evidence"] else ""
        if item["missing_evidence"]:
            extra = " — ⚠ evidence required but missing"
        followed.append(
            f"[{mark}] {item['title']} ({item['status']}, "
            f"{FOLLOW_UP_LABELS.get(item['follow_up'], item['follow_up'])}){extra}")

    deadlines = [f"`{d['due']}` ({d['days_left']:+d}d, {_LEVEL_LABEL[d['level']]}) — {d['title']}"
                 for d in verification["deadlines"] if d["level"] != "done"]
    responsibles = ", ".join(r["email"] for r in track.get("responsibles", [])) or "pending"

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- None."

    return f"""# EOD report - {state['employee_name']} - {verification['date']}

**To:** {responsibles}
**Track:** {track.get('name')} | **Profile:** {state['profile_id']}
**Check-ins today:** AM {'yes' if verification['checked_in_am'] else 'NO'} / PM {'yes' if verification['checked_in_pm'] else 'NO'}
**Overall:** {verification['tasks_done']}/{verification['tasks_total']} tasks done ({int(verification['completion_rate'] * 100)}%)
**Today's follow-up:** {verification['touched_today']} touched / {verification['pending_today']} untouched

## Summary

{summary or 'Deterministic report (LLM summary disabled).'}

## Tasks followed up today

{bullets(followed)}

## Blockers

{bullets(verification['blockers'])}

## Deadlines

{bullets(deadlines)}

---
*Simulated delivery: in production this report is sent to Teams and persisted in DynamoDB.*
"""


def save_eod_report(report_md: str, employee_email: str, on_date: str) -> str:
    """Store the EOD report. Local disk by default, or S3 when BENCH_DOCS_S3_BUCKET is
    set (bench/docstore). Returns a local path or an s3:// URI. (Write tool)"""
    from bench.docstore import put_report

    employee_email = normalize_email(employee_email)
    filename = f"{on_date}_{employee_email.replace('@', '_at_')}.md"
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        person = conn.execute(
            "SELECT person_id FROM people WHERE email_normalized = ?",
            (employee_email,),
        ).fetchone()
        if person is None:
            raise KeyError(f"No person for '{employee_email}'")
        outbox_id = conn.execute(
            "INSERT INTO report_outbox "
            "(filename, employee_email, person_id, on_date, report_md, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filename, employee_email, person["person_id"] if person else None,
             on_date, report_md, now, now),
        ).lastrowid
    try:
        path = put_report(filename, report_md)
    except Exception as exc:
        _mark_report_outbox_failed(outbox_id, str(exc))
        raise
    _complete_report_outbox(outbox_id, path)
    return path


def _mark_report_outbox_failed(outbox_id: int, error: str) -> None:
    try:
        with connect() as conn:
            conn.execute(
                "UPDATE report_outbox SET status = 'failed', error = ?, updated_at = ? "
                "WHERE id = ? AND status != 'completed'",
                (error[:1000], datetime.now(timezone.utc).isoformat(), outbox_id),
            )
    except Exception:
        # Preserve the external document error; reconciliation can retry the pending row.
        pass


def _complete_report_outbox(outbox_id: int, path: str) -> None:
    with connect() as conn:
        row = conn.execute(
            "SELECT filename, person_id, on_date FROM report_outbox "
            "WHERE id = ? AND status != 'completed'",
            (outbox_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"No pending report outbox row for id {outbox_id}")
        conn.execute(
            "UPDATE report_outbox SET external_path = ?, status = 'completed', error = NULL, "
            "updated_at = ? WHERE id = ? AND status != 'completed'",
            (path, datetime.now(timezone.utc).isoformat(), outbox_id),
        )
        append_audit(
            conn, entity_type="report", entity_id=row["filename"],
            person_id=row["person_id"],
            action="save_eod_report", context={"path": path, "date": row["on_date"]},
        )


def reconcile_report_outbox(limit: int = 100) -> int:
    """Retry pending/failed external report writes and finalize their audits."""
    from bench.docstore import put_report

    if limit < 1:
        raise ValueError("limit must be positive")
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, filename, report_md FROM report_outbox "
            "WHERE status IN ('pending', 'failed') ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
    completed = 0
    for row in rows:
        try:
            path = put_report(row["filename"], row["report_md"])
            _complete_report_outbox(row["id"], path)
        except Exception as exc:
            _mark_report_outbox_failed(row["id"], str(exc))
            continue
        completed += 1
    return completed
