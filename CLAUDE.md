# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
cd backend
pip install -r requirements.txt

# Run the full analysis pipeline (processes all transcripts in mock_transcripts/)
python agent/hub_spoke.py

# Validate generated JSON outputs against the schema
python agent/verify_outputs.py
```

The project uses a `.venv` at the repo root. Activate it with `source .venv/bin/activate` before running.

Environment requires a `backend/.env` file with `ANTHROPIC_API_KEY`. The process raises `RuntimeError` at startup if the key is missing.

## Architecture

This is a **hub-and-spoke multi-agent QA system** for analyzing hospital support call recordings using the Claude Agent SDK (`claude_agent_sdk`).

### Execution flow

1. `main()` in `backend/agent/hub_spoke.py` finds all `.txt` transcripts in `backend/mock_transcripts/`
2. For each transcript, a **coordinator agent** receives the full transcript text
3. The coordinator dispatches to three **specialized subagents** via MCP tool calls (can run in parallel):
   - `mcp__qa_tools__analyze_agent_tone` — evaluates support agent professionalism, empathy, clarity, helpfulness, de-escalation
   - `mcp__qa_tools__analyze_patient_tone` — evaluates patient respectfulness, clarity, cooperation, emotional regulation, escalation
   - `mcp__qa_tools__analyze_call_outcome` — assesses resolution, next-step clarity, PHI compliance, safety risk, escalation necessity
4. Each tool calls `claude-sonnet-4-20250514` with a specialized system prompt and returns a JSON string with five 1–10 integer scores plus a `notes` field
5. A `PostToolUse` hook in the coordinator validates each tool's JSON immediately; malformed or missing fields trigger retry feedback to the subagent
6. The coordinator assembles a final report, validated against `JSON_SCHEMA` from `backend/agent/schema.py`, and writes it to `backend/output/{transcript_stem}.json`

### Key files

| File | Role |
|------|------|
| `backend/agent/hub_spoke.py` | Entry point; coordinator agent definition, tool registration, MCP server setup, hook logic |
| `backend/agent/schema.py` | JSON schema definition, `validate_report()`, `validate_reviewer()` |
| `backend/tools/tool_agent_tone.py` | `@tool()`-decorated function for agent tone analysis |
| `backend/tools/tool_patient_tone.py` | `@tool()`-decorated function for patient tone analysis |
| `backend/tools/tool_call_outcome.py` | `@tool()`-decorated function for call outcome assessment |

### Output schema

```json
{
  "transcript_id": "string",
  "agent_tone_reviewer":   { "professionalism": 1-10, "empathy": 1-10, "clarity": 1-10, "helpfulness": 1-10, "de_escalation": 1-10, "notes": "string" },
  "patient_tone_reviewer": { "respectfulness": 1-10, "clarity": 1-10, "cooperation": 1-10, "emotional_regulation": 1-10, "escalation_intensity": 1-10, "notes": "string" },
  "call_outcome_reviewer": { "resolution": 1-10, "next_step_clarity": 1-10, "phi_compliance": 1-10, "safety_risk": 1-10, "escalation_necessity": 1-10, "notes": "string" },
  "coordinator_summary": "string"
}
```

`additionalProperties: false` is enforced on all blocks. Schema uses `integer` not `number`; booleans must be rejected explicitly because `bool` is a subclass of `int` in Python.

### Error handling pattern

Tools return structured error JSON (not exceptions) with `errorCategory`, `isRetryable`, and `context` fields. The `PostToolUse` hook distinguishes retryable errors (rate limit, timeout) from non-retryable ones (auth failure, invalid input) and feeds context-specific messages back to the subagent.
