from pathlib import Path
from typing import Any

import yaml

from bench.config import TRACKS_DIR


def load_track(track_id: str) -> dict[str, Any]:
    """Load a bench track by id from tracks/<id>.yaml. (Read tool)"""
    path = Path(TRACKS_DIR) / f"{track_id}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in Path(TRACKS_DIR).glob("*.yaml"))
        raise FileNotFoundError(f"Track '{track_id}' not found. Available: {available}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
