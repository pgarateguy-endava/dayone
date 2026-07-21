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


# --- AWS integrations (consumed from local; each has a local fallback) ---

def storage_backend() -> str:
    """Per-person state store: 'dynamodb' when BENCH_STORAGE=dynamodb, else 'sqlite'.
    Read at call time so tests can flip it. The catalog always stays in SQLite."""
    return "dynamodb" if os.environ.get("BENCH_STORAGE", "").lower() == "dynamodb" else "sqlite"


def docs_s3_bucket() -> str | None:
    """When set (BENCH_DOCS_S3_BUCKET), EOD reports and profile PDFs go to S3;
    otherwise they stay on local disk. Read at call time."""
    return os.environ.get("BENCH_DOCS_S3_BUCKET") or None


def dynamodb_table_prefix() -> str:
    """Prefix for the per-person DynamoDB tables (default 'bench')."""
    return os.environ.get("BENCH_DYNAMODB_PREFIX", "bench")


def aws_region() -> str:
    return os.environ.get("AWS_REGION", BEDROCK_REGION)


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
