from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKS_DIR = REPO_ROOT / "tracks"
PROGRESS_DIR = REPO_ROOT / ".local-progress"
REPORTS_DIR = PROGRESS_DIR / "reports"
