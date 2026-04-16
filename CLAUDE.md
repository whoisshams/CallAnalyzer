# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CallRecordingAnalyzer is a two-stage pipeline that transcribes audio call recordings and reformats the transcript by labeling each speaker role (Interviewer/Interviewee).

## Setup

Requires a `.env` file in the project root with:
```
OPENAI_API_KEY=your_key_here
```

Install dependencies:
```bash
pip install openai python-dotenv
```

## Running the Pipeline

**Step 1 — Transcribe audio to text:**
```bash
cd backend
python transcription.py
```
Reads `demo_interview.mp3`, calls OpenAI `gpt-4o-transcribe`, writes raw transcript to `transcription_sample.txt`.

**Step 2 — Label speakers:**
```bash
cd backend
python final_transcription.py
```
Reads `transcription_sample.txt`, calls OpenAI `gpt-4o` to reformat with `Interviewer:` / `Interviewee:` labels, prints to stdout.

## Architecture

- `backend/transcription.py` — Audio → raw text via `client.audio.transcriptions.create()` (model: `gpt-4o-transcribe`). Includes a domain-specific prompt to help the model understand the call context (hospital/appointment support).
- `backend/final_transcription.py` — Raw text → labeled transcript via `client.responses.create()` (model: `gpt-4o`). Uses a system prompt instructing the model to assign speaker roles.
- `backend/transcription_sample.txt` — Intermediate file shared between the two scripts. The first script writes it; the second reads it.
- `frontend/` — Currently empty; intended for a UI layer.

## Code Style

- Comments should be rare. Only add them for genuinely complex or non-obvious logic — not for straightforward lines and not frequently throughout generated code.

## Key Notes

- File paths in both scripts are currently hardcoded as absolute paths — update them when moving the project or changing the audio source.
- The two scripts are independent and must be run in order; `final_transcription.py` depends on `transcription_sample.txt` existing.
