"""
Hospital call QA using the Claude Agent SDK (hub-and-spoke).

What this file does, top to bottom:
1. Load env + SDK.
2. Define 3 tools that ask Claude for a JSON score block.
3. Host those tools in a local MCP server.
4. Define 3 subagents (spokes), each with ONE tool.
5. Define a PostToolUse hook that validates each tool's JSON.
6. Configure the coordinator (hub) with a strict output JSON schema.
7. Loop over every transcript in `mock_transcripts/` and save one JSON
   report per transcript in `output/`.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Make `backend/` importable so `from tools....` works when running this file directly.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(_BACKEND_ROOT / ".env")

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError("Missing ANTHROPIC_API_KEY. Add it to backend/.env.")

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    HookMatcher,
    create_sdk_mcp_server,
    query,
    tool,
)

from agent.schema import JSON_SCHEMA, validate_report, validate_reviewer
from tools.tool_agent_tone import analyze_agent_tone
from tools.tool_call_outcome import analyze_call_outcome
from tools.tool_patient_tone import analyze_patient_tone

'''What makes a great tool description:
•
- Clear purpose: What the tool does in one sentence
•
- Input specifications: Exact types, formats, ranges, and constraints
•
- Examples: Show expected input/output pairs for common cases
•
- Edge cases: Document what happens with empty inputs, invalid data, boundary values
•
- When NOT to use: Clarify tool boundaries to prevent misuse
'''
# 1. Wrap Python functions as SDK tools.
#    Tools must be async and return MCP tool-result shape.
# Tool description answers: "How do I call this tool correctly?"
@tool(
    "analyze_agent_tone",
    (
        "Analyze ONLY the support agent's behavior in a hospital call transcript. "
        "Input: raw transcript text with speaker turns (e.g. 'Agent: ... Patient: ...'). "
        "Do NOT pass an empty string. Do NOT use this tool to assess the patient. "
        "Returns a JSON object with integer scores 1–10 for: professionalism, empathy, "
        "clarity, helpfulness, de_escalation, and a non-empty 'notes' string. "
        "Example output: {\"professionalism\": 8, \"empathy\": 7, \"clarity\": 9, "
        "\"helpfulness\": 8, \"de_escalation\": 6, \"notes\": \"Agent stayed calm.\"}. "
        "Returns a JSON parse error description if the model output is malformed."
    ),
    {"transcript": str},
)

async def analyze_agent_tone_tool(args):
    return {"content": [{"type": "text", "text": analyze_agent_tone(args["transcript"])}]}


@tool(
    "analyze_patient_tone",
    (
        "Analyze ONLY the patient's behavior in a hospital call transcript. "
        "Input: raw transcript text with speaker turns (e.g. 'Agent: ... Patient: ...'). "
        "Do NOT pass an empty string. Do NOT use this tool to assess the support agent. "
        "Returns a JSON object with integer scores 1–10 for: respectfulness, clarity, "
        "cooperation, emotional_regulation, escalation_intensity, and a non-empty 'notes' string. "
        "Example output: {\"respectfulness\": 6, \"clarity\": 7, \"cooperation\": 5, "
        "\"emotional_regulation\": 4, \"escalation_intensity\": 8, \"notes\": \"Patient was agitated.\"}. "
        "Returns a JSON parse error description if the model output is malformed."
    ),
    {"transcript": str},
)
async def analyze_patient_tone_tool(args):
    return {"content": [{"type": "text", "text": analyze_patient_tone(args["transcript"])}]}


@tool(
    "analyze_call_outcome",
    (
        "Assess the overall outcome of a hospital call, evaluating both parties together. "
        "Input: raw transcript text with speaker turns (e.g. 'Agent: ... Patient: ...'). "
        "Do NOT pass an empty string. Use this tool only after both agent and patient tones have been scored. "
        "Returns a JSON object with integer scores 1–10 for: resolution_completeness, next_step_clarity, "
        "phi_compliance, safety_risk, escalation_necessity, and a non-empty 'notes' string. "
        "Example output: {\"resolution_completeness\": 7, \"next_step_clarity\": 8, "
        "\"phi_compliance\": 10, \"safety_risk\": 2, \"escalation_necessity\": 3, "
        "\"notes\": \"Issue resolved; no PHI breach.\"}. "
        "Returns a JSON parse error description if the model output is malformed."
    ),
    {"transcript": str},
)
async def analyze_call_outcome_tool(args):
    return {"content": [{"type": "text", "text": analyze_call_outcome(args["transcript"])}]}


# 2. Host the tools in a local MCP server.
#    Tool names become `mcp__qa_tools__<tool_name>` when referenced elsewhere.
qa_server = create_sdk_mcp_server(
    name="qa_tools",
    version="1.0.0"
    ,
    tools=[analyze_agent_tone_tool, 
           analyze_patient_tone_tool, 
           analyze_call_outcome_tool
           ],
)


# 3. One subagent per reviewer. Each one can only call its own tool.
# Agent prompt answers: "What is my job in this session?"
agents = {
    "agent_tone_reviewer": AgentDefinition(
        description=(
            "QA reviewer responsible ONLY for the support agent's tone. "
            "Scores professionalism, empathy, clarity, helpfulness, and de-escalation. "
            "Does NOT assess the patient."
        ),
        prompt=(
            "You are a hospital QA reviewer assessing the support agent's tone. "
            "Call analyze_agent_tone exactly once, passing the full transcript text provided. "
            "If the transcript appears short or one-sided, still call the tool once — do not skip it. "
            "Return ONLY the raw JSON object from the tool result. "
            "Do not add any explanation, commentary, or extra text around the JSON."
        ),
        tools=["mcp__qa_tools__analyze_agent_tone"],
    ),
    "patient_tone_reviewer": AgentDefinition(
        description=(
            "QA reviewer responsible ONLY for the patient's tone. "
            "Scores respectfulness, clarity, cooperation, emotional regulation, and escalation intensity. "
            "Does NOT assess the support agent."
        ),
        prompt=(
            "You are a hospital QA reviewer assessing the patient's tone. "
            "Call analyze_patient_tone exactly once, passing the full transcript text provided. "
            "If the transcript appears short or one-sided, still call the tool once — do not skip it. "
            "Return ONLY the raw JSON object from the tool result. "
            "Do not add any explanation, commentary, or extra text around the JSON."
        ),
        tools=["mcp__qa_tools__analyze_patient_tone"],
    ),
    "call_outcome_reviewer": AgentDefinition(
        description=(
            "QA reviewer responsible for the overall call outcome and compliance. "
            "Scores resolution completeness, next-step clarity, PHI compliance, safety risk, "
            "and escalation necessity across both parties."
        ),
        prompt=(
            "You are a hospital QA reviewer assessing the overall call outcome and compliance. "
            "Call analyze_call_outcome exactly once, passing the full transcript text provided. "
            "If the transcript appears short or one-sided, still call the tool once — do not skip it. "
            "Return ONLY the raw JSON object from the tool result. "
            "Do not add any explanation, commentary, or extra text around the JSON."
        ),
        tools=["mcp__qa_tools__analyze_call_outcome"],
    ),
}


# 4. PostToolUse hook = our validator.
#    It runs right after a reviewer tool returns its JSON string.
#    - If valid: we accept it (return empty dict).
#    - If invalid: we tell the subagent what's wrong so it can retry.
TOOL_TO_REVIEWER = {
    "mcp__qa_tools__analyze_agent_tone": "agent_tone_reviewer",
    "mcp__qa_tools__analyze_patient_tone": "patient_tone_reviewer",
    "mcp__qa_tools__analyze_call_outcome": "call_outcome_reviewer",
}

# gets the text from the tool response
def _get_tool_text(tool_response: Any) -> str:
    if not isinstance(tool_response, dict):
        return ""
    parts = []
    for item in tool_response.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text") or "")
    return "\n".join(parts).strip()

# checks if the tool output is not valid json
async def validate_tool_output(hook_input: dict[str, Any], *_: Any) -> dict[str, Any]:
    reviewer = TOOL_TO_REVIEWER.get(hook_input.get("tool_name"))
    if not reviewer:
        return {}

    raw_text = _get_tool_text(hook_input.get("tool_response"))

    # Try to parse as JSON.
    try:
        data = json.loads(raw_text) if raw_text else None
    except json.JSONDecodeError as exc:
        return _hook_feedback(f"{reviewer} output was not valid JSON: {exc}")

    # Validate the shape.
    error = validate_reviewer(reviewer, data)
    if error:
        return _hook_feedback(f"{reviewer} JSON is invalid: {error}")

    return {}

# this is for the hook_feedback when json is not valid
def _hook_feedback(message: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"{message}. Retry the tool and return ONLY a JSON object "
                "with the required integer 1-10 score fields and a non-empty 'notes' string."
            ),
        }
    }


# 5. Coordinator (hub) configuration.
#    - `agents={...}` auto-enables the built-in Task tool.
#    - `output_format=json_schema` forces the final answer to be valid JSON.
options = ClaudeAgentOptions(
    system_prompt=(
        "You coordinate hospital call QA. In one response, issue Task calls to "
        "agent_tone_reviewer, patient_tone_reviewer, and call_outcome_reviewer "
        "in parallel. Then return ONE final JSON object matching the required schema. "
        "Use the `transcript_id` given in the user prompt."
    ),
    output_format={"type": "json_schema", "schema": JSON_SCHEMA},
    mcp_servers={"qa_tools": qa_server},
    agents=agents,
    allowed_tools=["Task"],
    permission_mode="bypassPermissions",
    hooks={
        "PostToolUse": [
            HookMatcher(
                matcher="|".join(TOOL_TO_REVIEWER.keys()),
                hooks=[validate_tool_output],
                timeout=30.0,
            )
        ]
    },
)
# Concrete Token Comparison
#Approach	Transcript tokens per run	Total over 5 runs
#Current (fresh session each time)	4,000 lines × 4 = ~16,000 tokens	~80,000 tokens
#Two-stage (Stage 1 once, Stage 2 resumes)	Stage 1: ~16,000. Stage 2: ~0	~16,000 + (4 × ~500) = ~18,000 tokens

async def _run_coordinator(prompt: str) -> dict[str, Any]:
    """
    Run the coordinator once and return the structured JSON output.

    Because we set output_format=json_schema, the SDK returns the final
    answer on ResultMessage.structured_output as a real Python dict.
    """
    structured = None
    session_id = None
    async for message in query(prompt=prompt, options=options):
        if session_id is None:
            session_id = getattr(message, "session_id", None)
        candidate = getattr(message, "structured_output", None)
        if isinstance(candidate, dict):
            structured = candidate

    print(f"Session ID: {session_id}")

    if structured is None:
        raise RuntimeError("Coordinator did not return a structured JSON result.")

    return structured


# 6. Process each transcript file.
async def process_transcript(file_path: Path) -> None:
    transcript = file_path.read_text(encoding="utf-8").strip()
    if not transcript:
        print(f"{file_path.name}: skipped (empty file)")
        return

    prompt = (
        f"TRANSCRIPT_ID: {file_path.name}\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        "Delegate to all three reviewers in parallel, then return the final JSON."
    )

    data = await _run_coordinator(prompt)

    error = validate_report(data)
    if error:
        raise RuntimeError(f"{file_path.name}: invalid report - {error}")

    out_path = _BACKEND_ROOT / "output" / f"{file_path.stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print(f"{file_path.name}: OK -> {out_path.relative_to(_BACKEND_ROOT)}")


async def main() -> None:
    transcripts = sorted((_BACKEND_ROOT / "mock_transcripts").glob("*.txt"))
    if not transcripts:
        raise RuntimeError("No transcripts found in backend/mock_transcripts/")

    for file_path in transcripts:
        await process_transcript(file_path)


if __name__ == "__main__":
    asyncio.run(main())

