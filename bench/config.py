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
