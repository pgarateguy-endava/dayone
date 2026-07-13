"""BenchCoach — Teams bot as a THIN CHANNEL over the Bench service (ADR 0004).

The bot holds no domain logic, no persistent state and no AWS credentials.
Everything is forwarded over HTTP to the Bench service (`bench/api.py`, /api/v1),
which owns the catalog, the LangGraph daily cycle and the Bedrock calls.

Ephemeral state kept here (channel UX only): the guided onboarding step and the
resolved employee email per conversation.
"""
import asyncio
from typing import Any

import httpx
from azure.identity import ManagedIdentityCredential
from microsoft_teams.api import MessageActivity, TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

from config import Config

config = Config()

# conversation+user -> {"email": str | None, "onboarding": dict | None}
CHANNEL_STATE: dict[str, dict[str, Any]] = {}

HELP = (
    "**BenchCoach** — tu asistente de Bench.\n\n"
    "- `start bench` — crear tu plan (elegís rol y track)\n"
    "- `plan` — ver tu plan\n"
    "- `tasks` — tus tareas con estado\n"
    "- `done <n> <evidencia>` — marcar tarea, ej: `done 3 curso al 45%`\n"
    "- `checkin am` / `checkin pm [bloqueos]` — check-in diario\n"
    "- `report` — reporte EOD\n"
    "- cualquier otra cosa — chat con la IA sobre tu avance\n"
)


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


def channel_state(ctx: ActivityContext[MessageActivity]) -> dict[str, Any]:
    key = f"{ctx.activity.conversation.id}:{ctx.activity.from_.id}"
    return CHANNEL_STATE.setdefault(key, {"email": None, "onboarding": None})


async def resolve_email(ctx: ActivityContext[MessageActivity], state: dict[str, Any]) -> str | None:
    """Resolve the user's corporate email via the conversation members API."""
    if state["email"]:
        return state["email"]
    try:
        member = await ctx.api.conversations.members(ctx.activity.conversation.id).get(
            ctx.activity.from_.id)
        email = getattr(member, "email", None) or getattr(member, "user_principal_name", None)
    except Exception:
        email = None
    state["email"] = email
    return email


async def backend(method: str, path: str, json: dict | None = None) -> dict:
    async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=60) as client:
        response = await client.request(method, path, json=json)
    if response.status_code == 404:
        return {"reply": response.json().get("detail", "No estás en bench todavía. "
                                                       "Escribí `start bench` para empezar.")}
    response.raise_for_status()
    return response.json()


async def handle_onboarding(ctx, state, email: str, text: str) -> bool:
    """Two-step guided intake: role -> track -> POST /onboard. Returns True if handled."""
    flow = state["onboarding"]
    if text.lower() in ("start bench", "empezar bench", "bench start", "alta"):
        cat = await backend("GET", "/api/v1/catalog")
        state["onboarding"] = {"step": "role", "catalog": cat}
        roles = "\n".join(f"- `{p['id']}` — {p['name']}" for p in cat["profiles"])
        await ctx.send(f"¡Vamos! ¿Cuál es tu rol? Respondé con el id:\n\n{roles}")
        return True
    if not flow:
        return False
    if flow["step"] == "role":
        role = text.strip().lower()
        if role not in [p["id"] for p in flow["catalog"]["profiles"]]:
            await ctx.send("No conozco ese rol — respondé con uno de los ids de la lista.")
            return True
        flow["role"], flow["step"] = role, "track"
        tracks = [t for t in flow["catalog"]["tracks"] if role in t["target_profiles"]] \
            or flow["catalog"]["tracks"]
        flow["track_options"] = [t["id"] for t in tracks]
        options = "\n".join(f"- `{t['id']}` — {t['name']}" for t in tracks)
        await ctx.send(f"¿Qué track vas a seguir?\n\n{options}")
        return True
    if flow["step"] == "track":
        track = text.strip().lower()
        if track not in flow["track_options"]:
            await ctx.send("Ese track no está en la lista — respondé con uno de los ids.")
            return True
        result = await backend("POST", "/api/v1/onboard", {
            "employee_name": ctx.activity.from_.name or email,
            "employee_email": email, "profile_id": flow["role"], "track_id": track,
        })
        state["onboarding"] = None
        await ctx.send(result["reply"])
        return True
    return False


def parse_done(text: str) -> dict | None:
    """'done 3 curso al 45%' -> {"task_id": 3, "status": "done", "evidence": ...}"""
    parts = text.split(maxsplit=2)
    if len(parts) >= 2 and parts[0].lower() in ("done", "hecho") and parts[1].isdigit():
        return {"task_id": int(parts[1]), "status": "done",
                "evidence": parts[2] if len(parts) > 2 else ""}
    return None


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.reply(TypingActivityInput())
    text = (ctx.activity.strip_mentions_text().text or "").strip()
    state = channel_state(ctx)
    lowered = text.lower()

    if lowered in ("hello", "hi", "hola", "help", "ayuda", "?"):
        await ctx.send(HELP)
        return

    email = await resolve_email(ctx, state)
    if not email:
        if lowered.startswith("email "):
            state["email"] = text.split(maxsplit=1)[1].strip()
            await ctx.send(f"Listo, te identifico como **{state['email']}**. Escribí `help`.")
        else:
            await ctx.send("No pude resolver tu email de Teams. "
                           "Decime quién sos: `email tu.nombre@endava.com`")
        return

    try:
        if await handle_onboarding(ctx, state, email, text):
            return
        done = parse_done(text)
        if done:
            result = await backend("POST", "/api/v1/task", {"employee_email": email, **done})
        elif lowered.startswith("checkin"):
            parts = text.split(maxsplit=2)
            period = parts[1].lower() if len(parts) > 1 and parts[1].lower() in ("am", "pm") else "pm"
            blockers = parts[2] if len(parts) > 2 else ""
            result = await backend("POST", "/api/v1/checkin", {
                "employee_email": email, "period": period, "blockers": blockers})
        elif lowered in ("plan", "mi plan"):
            result = await backend("GET", f"/api/v1/plan/{email}")
        elif lowered in ("tasks", "tareas", "mis tareas"):
            result = await backend("GET", f"/api/v1/tasks/{email}")
        elif lowered in ("report", "reporte", "summary", "resumen", "eod"):
            result = await backend("GET", f"/api/v1/report/{email}")
        else:
            result = await backend("POST", "/api/v1/chat", {
                "employee_email": email, "text": text,
                "conversation_id": ctx.activity.conversation.id})
        await ctx.send(result["reply"])
    except httpx.HTTPError:
        await ctx.send("No pude hablar con el servicio de Bench 😕 — "
                       f"¿está corriendo en `{config.BACKEND_URL}`?")


if __name__ == "__main__":
    asyncio.run(app.start())
