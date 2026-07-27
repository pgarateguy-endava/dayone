"""DynamoDB backend for per-person notification state (AWS integration, from local).

Scope (per the roadmap): the KV-shaped per-person tables — `conversation_refs` and
`notifications` — move to DynamoDB when BENCH_STORAGE=dynamodb. The join-heavy tables
(`people`, `person_tasks`) stay in SQLite for now; porting them is the next increment.

Tables are created on demand (no infra step for the demo). Default is SQLite, so this
path can never affect the demo unless the flag is set explicitly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from bench.config import aws_region, dynamodb_table_prefix


def _resource():
    import boto3

    return boto3.resource("dynamodb", region_name=aws_region())


class _TableMissing(Exception):
    """The table does not exist yet (or is being deleted). Reads treat this as empty."""


def _table(name: str, key: str, create: bool = True):
    """Return a table handle. Creates the table (PK=`key`) on first use when create=True;
    when create=False and the table is absent/half-deleted, raises _TableMissing so
    read paths can treat it as empty (avoids 500s right after a reset)."""
    import time

    resource = _resource()
    full = f"{dynamodb_table_prefix()}-{name}"
    table = resource.Table(full)
    try:
        table.load()
        # A table mid-delete still 'loads' but isn't usable — wait it out.
        if table.table_status == "DELETING":
            while True:
                time.sleep(1)
                try:
                    table.reload()
                except Exception:
                    break  # gone
        else:
            return table
    except Exception:
        pass  # not found — fall through to create-or-signal
    if not create:
        raise _TableMissing(full)
    table = resource.create_table(
        TableName=full,
        KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


def _convrefs():
    return _table("conversation-refs", "email")


def _notifications():
    return _table("notifications", "id")


# --- conversation refs ---

def save_conversation_ref(email: str, conversation_id: str) -> None:
    _convrefs().put_item(Item={
        "email": email, "conversation_id": conversation_id,
        "updated_at": datetime.now(timezone.utc).isoformat()})


def get_conversation_ref(email: str) -> str | None:
    try:
        item = _table("conversation-refs", "email", create=False).get_item(
            Key={"email": email}).get("Item")
    except _TableMissing:
        return None
    return item.get("conversation_id") if item else None


def has_conversation_ref(email: str) -> bool:
    return get_conversation_ref(email) is not None


# --- notifications ---

def queue_notification(email: str, kind: str, message: str) -> None:
    _notifications().put_item(Item={
        "id": str(uuid.uuid4()), "email": email, "kind": kind, "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(), "delivered_at": None})


def _all_notifications() -> list[dict]:
    # Demo/pilot scale: a scan is fine. Production would use a GSI on (email, kind).
    try:
        return _table("notifications", "id", create=False).scan().get("Items", [])
    except _TableMissing:
        return []


def already_sent(email: str, kind: str, since_days: int | None = None) -> bool:
    items = [n for n in _all_notifications() if n["email"] == email and n["kind"] == kind]
    if since_days is not None:
        from datetime import date, timedelta

        cutoff = (date.today() - timedelta(days=since_days)).isoformat()
        items = [n for n in items if n["created_at"][:10] >= cutoff]
    return len(items) > 0


def delivered(email: str, kind: str) -> bool:
    return any(n["email"] == email and n["kind"] == kind and n.get("delivered_at")
               for n in _all_notifications())


def pending_notifications() -> list[dict]:
    items = [n for n in _all_notifications() if not n.get("delivered_at")]
    items.sort(key=lambda n: n["created_at"])
    for n in items:
        n["conversation_id"] = get_conversation_ref(n["email"])
    return items


def mark_delivered(notification_id: str) -> None:
    _notifications().update_item(
        Key={"id": notification_id},
        UpdateExpression="SET delivered_at = :d",
        ExpressionAttributeValues={":d": datetime.now(timezone.utc).isoformat()})


def clear_notifications(email: str) -> None:
    table = _notifications()
    for n in _all_notifications():
        if n["email"] == email:
            table.delete_item(Key={"id": n["id"]})


def notification_log(email: str | None = None) -> list[dict]:
    items = _all_notifications()
    if email:
        items = [n for n in items if n["email"] == email]
    items.sort(key=lambda n: n["created_at"], reverse=True)
    return items
