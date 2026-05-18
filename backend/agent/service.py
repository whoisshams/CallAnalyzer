# Author: Shams Anjum, 2026

"""This file is different from the ones that runs from the command line. It handles the API request and response."""

from typing import Any

from agent.demo import is_demo_mode, load_demo_report
from agent.hub_spoke import _run_coordinator
from agent.schema import validate_report


async def analyze_transcript(transcript_id: str, transcript: str) -> dict[str, Any]:
    """Run the existing agent pipeline for transcript text supplied by the API."""
    clean_transcript = transcript.strip()
    clean_transcript_id = transcript_id.strip()

    if not clean_transcript_id:
        raise ValueError("transcript_id must not be empty")
    if not clean_transcript:
        raise ValueError("transcript must not be empty")

    if is_demo_mode():
        data = load_demo_report(clean_transcript_id)
        if data is None:
            raise ValueError(
                "Demo mode is active. For a live analysis with your own transcript, "
                "contact the owner at whoisshams@gmail.com"
            )
        error = validate_report(data)
        if error:
            raise RuntimeError(f"{clean_transcript_id}: invalid demo report - {error}")
        return data

    prompt = (
        f"TRANSCRIPT_ID: {clean_transcript_id}\n"
        f"TRANSCRIPT:\n{clean_transcript}\n\n"
        "Delegate to all three reviewers in parallel, then return the final JSON."
    )

    data = await _run_coordinator(prompt)

    error = validate_report(data)
    if error:
        raise RuntimeError(f"{clean_transcript_id}: invalid report - {error}")

    return data
