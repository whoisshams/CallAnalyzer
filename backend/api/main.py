from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.service import analyze_transcript
from agent.service_stream import analyze_transcript_stream


app = FastAPI(title="Call Recording Analyzer API")

# Local frontend dev servers can call this API without browser CORS blocks.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://call-analyzer-coral.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

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
