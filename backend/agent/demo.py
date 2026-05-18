# Author: Shams Anjum, 2026

"""Canned reports for public demo mode (no Anthropic calls)."""

from __future__ import annotations

import json
import os
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEMO_FILES = {
    "smooth_call.txt": "smooth_call.json",
    "bad_agent.txt": "bad_agent.json",
    "bad_patient.txt": "bad_patient.json",
}


def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")


def load_demo_report(transcript_id: str) -> dict | None:
    name = _DEMO_FILES.get(transcript_id.strip())
    if not name:
        return None
    path = _BACKEND_ROOT / "output" / name
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
