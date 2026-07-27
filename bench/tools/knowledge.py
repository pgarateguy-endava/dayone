"""AI knowledge base: mandatory courses, certifications and suggested courses. (Read/Write)

This is the "info for the AI" grid — separate from the activation catalog (tracks).
Suggestions are deterministic: knowledge tags matched against the person's profile text;
the LLM narrates the result, it never invents courses or certs.
"""
from __future__ import annotations

from typing import Any

from bench.db import connect
from bench.tools.audit import append_audit


def list_knowledge(kind: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM knowledge" + (" WHERE kind = ?" if kind else "") + " ORDER BY kind, id"
    with connect() as conn:
        rows = conn.execute(query, (kind,) if kind else ()).fetchall()
    return [dict(r) for r in rows]


def add_knowledge(kind: str, title: str, provider: str = "", url: str = "",
                  register_url: str = "", tags: str = "", notes: str = "") -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO knowledge (kind, title, provider, url, register_url, tags, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kind, title, provider, url, register_url, tags, notes))
        append_audit(conn, entity_type="knowledge", entity_id=cursor.lastrowid,
                     action="add_knowledge", context={"kind": kind, "title": title})
        return cursor.lastrowid


def get_knowledge(item_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM knowledge WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(f"Knowledge item {item_id} not found")
        return dict(row)


def update_knowledge(item_id: int, *, title: str, provider: str = "", url: str = "",
                     register_url: str = "", tags: str = "", notes: str = "") -> None:
    with connect() as conn:
        updated = conn.execute(
            "UPDATE knowledge SET title = ?, provider = ?, url = ?, register_url = ?, "
            "tags = ?, notes = ? WHERE id = ?",
            (title, provider, url, register_url, tags, notes, item_id))
        if not updated.rowcount:
            return
        append_audit(conn, entity_type="knowledge", entity_id=item_id,
                     action="update_knowledge", context={"title": title})


def delete_knowledge(item_id: int) -> None:
    with connect() as conn:
        deleted = conn.execute("DELETE FROM knowledge WHERE id = ?", (item_id,))
        if not deleted.rowcount:
            return
        append_audit(conn, entity_type="knowledge", entity_id=item_id,
                     action="delete_knowledge")


def suggest_for_profile(profile_text: str) -> dict[str, list[dict]]:
    """Deterministic suggestions from the knowledge base.

    - mandatory courses: always included, for everyone.
    - certifications/courses: included when any of their tags appears in the profile
      text (e.g. profile mentions AWS -> AWS certs). Untagged items always match.
    """
    text = (profile_text or "").lower()
    mandatory, certifications, courses = [], [], []
    for item in list_knowledge():
        tags = [t.strip() for t in item["tags"].split(",") if t.strip()]
        matches = not tags or any(tag in text for tag in tags)
        if item["kind"] == "mandatory_course":
            mandatory.append(item)
        elif matches and item["kind"] == "certification":
            certifications.append(item)
        elif matches and item["kind"] == "course":
            courses.append(item)
    return {"mandatory": mandatory, "certifications": certifications, "courses": courses}
