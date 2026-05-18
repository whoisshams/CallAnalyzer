# Author: Shams Anjum, 2026

import os
import time

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.service import analyze_transcript
from agent.service_stream import analyze_transcript_stream


app = FastAPI(title="Call Recording Analyzer API")

# Local dev + stable Vercel production domain; regex covers preview deploy URLs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://call-analyzer-coral.vercel.app",
    ],
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_anthropic_cache: tuple[float, str, str] | None = None


def _anthropic_status() -> tuple[str, str]:
    """Cached probe: available, limited, or unavailable (+ user-facing message)."""
    global _anthropic_cache
    now = time.time()
    if _anthropic_cache and _anthropic_cache[0] > now:
        return _anthropic_cache[1], _anthropic_cache[2]

    if not os.getenv("ANTHROPIC_API_KEY"):
        result = ("unavailable", "API key not configured.")
    else:
        try:
            anthropic.Anthropic().messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            result = ("available", "AI analysis ready.")
        except anthropic.AuthenticationError:
            result = (
                "unavailable",
                "API credits reached. Contact owner to top up, or use demo samples.",
            )
        except anthropic.RateLimitError:
            result = ("limited", "Rate limited — try again shortly.")
        except Exception:
            result = ("unavailable", "AI temporarily unavailable.")

    _anthropic_cache = (now + 90, *result)
    return result


@app.get("/status")
def api_status() -> dict[str, str]:
    if os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes"):
        return {"api": "ok", "anthropic": "demo", "message": "Demo mode — use samples below. Live access: whoisshams@gmail.com"}
    state, message = _anthropic_status()
    return {"api": "ok", "anthropic": state, "message": message}

# AnalyzeTranscriptRequest is the request body used by the UI to submit transcript text for analysis. So this not used by the API.
class AnalyzeTranscriptRequest(BaseModel):
    """Request body used by the UI to submit transcript text for analysis."""

    transcript_id: str = Field(..., min_length=1, examples=["demo_call.txt"])
    transcript: str = Field(
        ...,
        min_length=1,
        examples=["Agent: Hello.\nPatient: I need help"],
    )

@app.post("/analyze")
async def analyze(request: AnalyzeTranscriptRequest) -> dict:
    """Analyze transcript text submitted by the UI and return the final QA report."""
    try:
        return await analyze_transcript(request.transcript_id, request.transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/analyze/stream")
async def analyze_stream(request: AnalyzeTranscriptRequest) -> StreamingResponse:
    """Stream analysis progress to the UI as Server-Sent Events in real time."""
    return StreamingResponse(
        analyze_transcript_stream(request.transcript_id, request.transcript),
        media_type="text/event-stream",
    )
