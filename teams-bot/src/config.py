import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration — thin channel: no Bedrock/AWS settings here (ADR 0004)."""

    APP_ID = os.environ.get("CLIENT_ID", "")
    APP_PASSWORD = os.environ.get("CLIENT_SECRET", "")
    APP_TYPE = os.environ.get("BOT_TYPE", "")
    APP_TENANTID = os.environ.get("TENANT_ID", "")

    # Bench service (bench/api.py) — the only backend the bot talks to.
    BACKEND_URL = os.environ.get("BENCH_BACKEND_URL", "http://localhost:8000")
