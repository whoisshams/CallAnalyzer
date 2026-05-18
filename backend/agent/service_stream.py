# Author: Shams Anjum, 2026

"""Streaming analysis using Server-Sent Events.

Yields one SSE per real backend checkpoint so the UI can show progress live.
Event types: 'progress' (a status line), 'result' (the final JSON), or 'error'.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from agent.demo import is_demo_mode, load_demo_report
from agent.hub_spoke import _run_coordinator_streamed
from agent.schema import validate_report


def _sse(event: str, payload) -> str:
    """Format a single Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


async def analyze_transcript_stream(
    transcript_id: str, transcript: str
) -> AsyncIterator[str]:
    """Stream progress events while the analysis pipeline runs."""
    transcript_id = transcript_id.strip()
    transcript = transcript.strip()

    if not transcript_id or not transcript:
        yield _sse("error", {"detail": "transcript_id and transcript must not be empty"})
        return

    if is_demo_mode():
        yield _sse("progress", "Demo mode — using saved sample report (no live AI).")
        data = load_demo_report(transcript_id)
        if data is None:
            yield _sse(
                "error",
                {
                    "detail": (
                        "Demo mode is active. For a live analysis with your own transcript, "
                        "contact the owner at whoisshams@gmail.com"
                    ),
                },
            )
            return
        error = validate_report(data)
        if error:
            yield _sse("error", {"detail": f"invalid demo report: {error}"})
            return
        yield _sse("progress", "Sample report loaded.")
        yield _sse("result", data)
        return

    # Fixed checkpoints that always run before the agent starts.
    yield _sse("progress", "Transcript received from frontend.")
    yield _sse("progress", "FastAPI request accepted.")
    yield _sse("progress", "Coordinator agent started.")

    prompt = (
        f"TRANSCRIPT_ID: {transcript_id}\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        "Delegate to all three reviewers in parallel, then return the final JSON."
    )

    try:
        data = None
        # _run_coordinator_streamed yields progress events in real time, then result.
        async for kind, payload in _run_coordinator_streamed(prompt):
            if kind == "progress":
                yield _sse("progress", payload)
            elif kind == "result":
                data = payload

        if data is None:
            yield _sse("error", {"detail": "Coordinator returned no result."})
            return

        error = validate_report(data)
        if error:
            yield _sse("error", {"detail": f"invalid report: {error}"})
            return

        yield _sse("progress", "Final report validated against JSON schema.")
        yield _sse("progress", "Structured QA report returned to frontend.")
        yield _sse("result", data)
    except Exception as exc:
        yield _sse("error", {"detail": str(exc)})
