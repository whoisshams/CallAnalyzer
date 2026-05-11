---

## description:

alwaysApply: true

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


| File                                 | Role                                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------ |
| `backend/agent/hub_spoke.py`         | Entry point; coordinator agent definition, tool registration, MCP server setup, hook logic |
| `backend/agent/schema.py`            | JSON schema definition, `validate_report()`, `validate_reviewer()`                         |
| `backend/tools/tool_agent_tone.py`   | `@tool()`-decorated function for agent tone analysis                                       |
| `backend/tools/tool_patient_tone.py` | `@tool()`-decorated function for patient tone analysis                                     |
| `backend/tools/tool_call_outcome.py` | `@tool()`-decorated function for call outcome assessment                                   |


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

### Project highlights for demos

- **Structured final output with `json_schema`**: The coordinator uses `output_format={"type": "json_schema", "schema": JSON_SCHEMA}` so the final QA report is consistent, machine-readable JSON instead of free-form model text.
- **Layered validation for reliability**: Reviewer results are validated immediately with a `PostToolUse` hook, and the complete report is validated again with `validate_report()` before writing output files.
- **Forced `tool_use` for reviewer scoring**: Each reviewer tool uses a schema-bound Anthropic tool call, which reduces malformed JSON, missing fields, incorrect types, and extra keys in subagent outputs.
- **Hub-and-spoke multi-agent architecture**: A coordinator delegates to focused reviewer agents for agent tone, patient tone, and call outcome, keeping each task narrow and easier to debug.
- **Local MCP server for custom QA tools**: The project exposes Python reviewer functions through a local MCP server, demonstrating practical agent-tool integration.
- **Model routing by task complexity**: Lightweight Haiku models handle focused reviewer work to reduce token usage, while the coordinator can use a stronger reasoning model for orchestration and synthesis.
- **Structured tool error handling**: Tools return predictable error payloads such as `{"isError": true, "errorCategory": "auth", "isRetryable": false, ...}`, making failures easier to classify and recover from.
- **Retry feedback through hooks**: When a reviewer output fails validation, the hook can feed targeted correction instructions back into the subagent loop.
- **Shared schema source of truth**: Reviewer score fields are centralized in `REVIEWER_FIELDS`, reducing drift between tool schemas, validation logic, and final report shape.
- **Parallel reviewer execution**: The coordinator can dispatch independent reviewers in parallel, improving throughput and keeping the system scalable.
- **Deterministic final safety gate**: The pipeline does not rely only on model behavior; Python validation rejects invalid reports before they are saved.
- **Clear separation of concerns**: Transcript loading, agent orchestration, reviewer scoring, schema validation, and output writing live in distinct modules.
- **Debuggable pipeline**: Hook logs and structured errors make it easier to identify whether a failure came from the model, tool, schema, or API layer.
- **Healthcare QA domain modeling**: The scoring dimensions map to realistic hospital support QA concerns such as professionalism, empathy, cooperation, PHI compliance, safety risk, and escalation need.

### Short Development Summary
**Every tool in the chain has one specific job:** React organizes your UI code. TypeScript prevents bugs while you write. Tailwind speeds up styling. Vite compiles everything and serves it during development. npm manages your libraries. Next.js adds routing and structure. Vercel hosts the compiled output. Your Python backend handles all server-side logic. The Anthropic SDK connects your Python code to Claude. HTTP and JSON are the language all of these pieces use to talk to each other.

### Future Optimizations
Api Wrapping for Frontend
prompt catching  
rate limiting  
Human-in-the-loop" (HITL) approvals.
use postgres
deploy with docker
use n8n later if possible
other token minimisation concepts
