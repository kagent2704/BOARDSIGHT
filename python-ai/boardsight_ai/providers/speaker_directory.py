from __future__ import annotations

import json
from pathlib import Path


def load_speaker_directory(project_root: Path) -> dict[str, dict]:
    directory_path = project_root / "python-ai" / "speaker_profiles.json"
    if not directory_path.exists():
        return {
            "Speaker-1": {"display_name": "Speaker-1", "designation": "Participant"},
            "Speaker-2": {"display_name": "Speaker-2", "designation": "Participant"},
            "Speaker-3": {"display_name": "Speaker-3", "designation": "Participant"},
        }

    try:
        return json.loads(directory_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "Speaker-1": {"display_name": "Speaker-1", "designation": "Participant"},
        }
