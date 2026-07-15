"""BenchCoach — Teams bot as a THIN CONVERSATIONAL CHANNEL (ADR 0004).

No commands, no domain logic, no state, no AWS credentials. The bot resolves the
user's corporate email, then forwards every message to the Bench service's
`POST /api/v1/chat`; the agent on the service side leads the conversation with its
tools (onboarding, task updates, check-ins, reports). The only thing kept here is the
resolved email per conversation (channel concern).
"""
import asyncio
from typing import Any

import httpx
from azure.identity import ManagedIdentityCredential
from microsoft_teams.api import MessageActivity, TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

from config import Config

config = Config()

EMAILS: dict[str, str] = {}  # conversation+user -> resolved email (ephemeral cache)


def create_token_factory():
    def get_token(scopes, tenant_id=None):
        credential = ManagedIdentityCredential(client_id=config.APP_ID)
        scopes_list = [scopes] if isinstance(scopes, str) else scopes
        token = credential.get_token(*scopes_list)
        return token.token

    return get_token


app = App(
    token=create_token_factory() if config.APP_TYPE == "UserAssignedMsi" else None,
    skip_auth=not config.APP_ID,
)


async def resolve_email(ctx: ActivityContext[MessageActivity]) -> str | None:
    key = f"{ctx.activity.conversation.id}:{ctx.activity.from_.id}"
    if key in EMAILS:
        return EMAILS[key]
    try:
        member = await ctx.api.conversations.members(ctx.activity.conversation.id).get(
            ctx.activity.from_.id)
        email = getattr(member, "email", None) or getattr(member, "user_principal_name", None)
    except Exception:
        email = None
    if email:
        EMAILS[key] = email
    return email


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.reply(TypingActivityInput())
    text = (ctx.activity.strip_mentions_text().text or "").strip()
    if not text:
        return

    email = await resolve_email(ctx)
    if not email:
        # Last-resort manual identification when the roster lookup is unavailable.
        if text.lower().startswith("email "):
            key = f"{ctx.activity.conversation.id}:{ctx.activity.from_.id}"
            EMAILS[key] = text.split(maxsplit=1)[1].strip()
            await ctx.send(f"Listo, te identifico como **{EMAILS[key]}**. ¿En qué te ayudo?")
        else:
            await ctx.send("No pude resolver tu email de Teams. "
                           "Decime quién sos: `email tu.nombre@endava.com`")
        return

    # Register the conversation reference so the service can message proactively.
    try:
        async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=10) as client:
            await client.post("/api/v1/conversation_ref", json={
                "email": email, "conversation_id": ctx.activity.conversation.id})
    except httpx.HTTPError:
        pass

    try:
        async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=90) as client:
            response = await client.post("/api/v1/chat", json={
                "employee_email": email,
                "text": text,
                "conversation_id": ctx.activity.conversation.id,
            })
        response.raise_for_status()
        await ctx.send(response.json()["reply"])
    except httpx.HTTPError:
        await ctx.send("No pude hablar con el servicio de Bench 😕 — "
                       f"¿está corriendo en `{config.BACKEND_URL}`?")


async def proactive_loop():
    """Poll the service for queued proactive notifications and deliver them in Teams."""
    from microsoft_teams.api import MessageActivityInput

    while True:
        await asyncio.sleep(20)
        try:
            async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=30) as client:
                response = await client.get("/api/v1/notifications/pending")
                for notification in response.json().get("notifications", []):
                    if not notification.get("conversation_id"):
                        continue  # person never talked to the bot yet — retry later
                    try:
                        await app.api.conversations.activities(
                            notification["conversation_id"]
                        ).create(MessageActivityInput(text=notification["message"]))
                        await client.post(
                            f"/api/v1/notifications/{notification['id']}/delivered")
                        print(f"[proactive] sent '{notification['kind']}' to {notification['email']}")
                    except Exception as exc:
                        print(f"[proactive] send failed for {notification['email']}: {exc!r}")
        except httpx.HTTPError:
            pass  # service down — retry next cycle


async def main():
    task = asyncio.create_task(proactive_loop())
    try:
        await app.start()
    finally:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
