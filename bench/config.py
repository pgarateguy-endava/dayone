import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

try:  # load repo-root .env (AWS/Bedrock + flags); existing env vars take precedence
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:  # pragma: no cover — dotenv optional, exports still work
    pass
TRACKS_DIR = REPO_ROOT / "tracks"
PROGRESS_DIR = REPO_ROOT / ".local-progress"
REPORTS_DIR = PROGRESS_DIR / "reports"

# Bedrock defaults, shared by every LLM surface (chat agent, daily-cycle summary,
# Strands variant) so they don't drift. ADR 0004: model access is in us-west-2.
BEDROCK_REGION = os.environ.get("AWS_REGION", "us-west-2")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")


# Shared bearer token guarding /api/v1. Unset => open (local dev/tests); set => required.
def api_token() -> str | None:
    """Read at call time so tests/pilots can set BENCH_API_TOKEN in the environment."""
    return os.environ.get("BENCH_API_TOKEN") or None


def bench_enabled() -> bool:
    """Feature flag: the Bench domain is opt-in (BENCH_ENABLED=1)."""
    return os.environ.get("BENCH_ENABLED", "0").lower() in ("1", "true", "yes")


def require_bench_enabled() -> None:
    """Gate for CLI entry points. Library functions stay importable for tests."""
    if not bench_enabled():
        raise SystemExit(
            "Bench domain is disabled. Enable it with BENCH_ENABLED=1 "
            "(export it or set it in .env — see .env.example)."
        )
