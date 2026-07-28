"""Append-only audit tools for SQLite-backed Bench mutations."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from bench.actor import current_actor
from bench.db import connect

MAX_CONTEXT_BYTES = 4096
_SENSITIVE_KEY = re.compile(
    r"(?:secret|token|password|credential|authorization|private[_-]?key|report[_-]?md|file[_-]?content|body)",
    re.IGNORECASE,
)


def _validate_context(value: Any, path: str = "context") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or _SENSITIVE_KEY.search(key):
                raise ValueError(f"audit context contains a sensitive key at {path}")
            _validate_context(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_context(child, f"{path}[{index}]")


def append_audit(
    conn: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: str | int | None,
    action: str,
    outcome: str = "succeeded",
    person_id: str | None = None,
    context: dict[str, Any] | None = None,
) -> int:
    """Append one audit record to the caller's active transaction."""
    actor = current_actor()
    if not actor.strip():
        raise ValueError("audit actor must not be blank")
    if not entity_type.strip() or not action.strip() or not outcome.strip():
        raise ValueError("audit entity_type, action, and outcome must not be blank")
    if context is not None and not isinstance(context, dict):
        raise TypeError("audit context must be a JSON object")
    _validate_context(context or {})
    actor = actor.strip()
    entity_type = entity_type.strip()
    action = action.strip()
    outcome = outcome.strip()
    payload = json.dumps(context or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ValueError(f"audit context exceeds {MAX_CONTEXT_BYTES} bytes")
    cursor = conn.execute(
        """INSERT INTO audit_log
           (at, actor, entity_type, entity_id, person_id, action, outcome, context)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now(timezone.utc).isoformat(), actor, entity_type,
         str(entity_id) if entity_id is not None else None, person_id,
         action, outcome, payload),
    )
    return int(cursor.lastrowid)


def list_action_history(
    *,
    person_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    action: str | None = None,
    outcome: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return deterministic newest-first audit rows."""
    if limit < 1:
        raise ValueError("limit must be positive")
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("entity_type", entity_type),
        ("entity_id", str(entity_id).strip() if entity_id is not None else None),
        ("action", action), ("outcome", outcome),
    ):
        if value is not None:
            if isinstance(value, str):
                value = value.strip()
            clauses.append(f"{column} = ?")
            params.append(value)
    query = "SELECT * FROM audit_log"
    if person_id is not None:
        clauses.insert(0, "(person_id = ? OR EXISTS (SELECT 1 FROM json_each(audit_log.context, '$.person_ids') WHERE json_each.value = ?))")
        params[0:0] = [person_id, person_id]
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    for row in rows:
        try:
            row["context"] = json.loads(row["context"])
        except (TypeError, json.JSONDecodeError):
            row["context"] = {"invalid_json": True}
    return rows
