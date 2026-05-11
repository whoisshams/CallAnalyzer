from typing import Any
# _run_coordinator is the function that runs the coordinator agent
from agent.hub_spoke import _run_coordinator
# validate_report is the function that validates the report
from agent.schema import validate_report


async def analyze_transcript(transcript_id: str, transcript: str) -> dict[str, Any]:
    """Run the existing agent pipeline for transcript text supplied by the API."""
    clean_transcript = transcript.strip()
    clean_transcript_id = transcript_id.strip()

    if not clean_transcript_id:
        raise ValueError("transcript_id must not be empty")
    if not clean_transcript:
        raise ValueError("transcript must not be empty")

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
