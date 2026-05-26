# Author: Shams Anjum, 2026

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

import argparse
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
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
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
'''Status Code	Error Type
400	BadRequestError
401	AuthenticationError
403	PermissionDeniedError
404	NotFoundError
422	UnprocessableEntityError
429	RateLimitError
>=500	InternalServerError
N/A	APIConnectionError'''


@tool(
    "analyze_agent_tone",
    (
        "Analyze ONLY the support agent's behavior in a hospital call transcript. "
        "Input: raw transcript text with speaker turns (e.g. 'Agent: ... Patient: ...'). "
        "Do NOT pass an empty string. Do NOT use this tool to assess the patient. "
        "Output: Returns a JSON object with integer scores 1–10 for: professionalism, empathy, "
        "clarity, and a non-empty 'notes' string. "
        "Example output: {\"professionalism\": 8, \"empathy\": 7, \"clarity\": 9, "
        "\"notes\": \"Agent stayed calm and explained the options clearly.\"}. "
        "Returns a JSON parse error description if the model output is malformed."
    ),
    {"transcript": str},
)

async def analyze_agent_tone_tool(args):
    # print("  -> analyze_agent_tone called", flush=True)
    transcript = args.get("transcript", "").strip()
    if not transcript:
        # Empty transcript (bad input)
        return {"content": [{"type": "text", "text": json.dumps({
            "isError": True, "errorCategory": "validation", "isRetryable": False,
            "context": {"attempted": "analyze_agent_tone", "reason": "transcript input was empty or missing"},
        })}]}
    return {"content": [{"type": "text", "text": analyze_agent_tone(transcript)}]}


@tool(
    "analyze_patient_tone",
    (
        "Analyze ONLY the patient's behavior in a hospital call transcript. "
        "Input: raw transcript text with speaker turns (e.g. 'Agent: ... Patient: ...'). "
        "Do NOT pass an empty string. Do NOT use this tool to assess the support agent. "
        "Returns a JSON object with integer scores 1–10 for: respectfulness, clarity, "
        "cooperation, and a non-empty 'notes' string. "
        "Example output: {\"respectfulness\": 6, \"clarity\": 7, \"cooperation\": 5, "
        "\"notes\": \"Patient was polite but a little vague.\"}. "
        "Returns a JSON parse error description if the model output is malformed."
    ),
    {"transcript": str},
)
async def analyze_patient_tone_tool(args):
    # print("  -> analyze_patient_tone called", flush=True)
    transcript = args.get("transcript", "").strip()
    if not transcript:
        return {"content": [{"type": "text", "text": json.dumps({
            "isError": True, "errorCategory": "validation", "isRetryable": False,
            "context": {"attempted": "analyze_patient_tone", "reason": "transcript input was empty or missing"},
        })}]}
    return {"content": [{"type": "text", "text": analyze_patient_tone(transcript)}]}


@tool(
    "analyze_call_outcome",
    (
        "Assess the overall outcome of a hospital call, evaluating both parties together. "
        "Input: raw transcript text with speaker turns (e.g. 'Agent: ... Patient: ...'). "
        "Do NOT pass an empty string. Use this tool only after both agent and patient tones have been scored. "
        "Returns a JSON object with integer scores 1–10 for: issue_resolved, next_step_clarity, "
        "privacy_handling, safety_risk, and a non-empty 'notes' string. "
        "Example output: {\"issue_resolved\": 7, \"next_step_clarity\": 8, "
        "\"privacy_handling\": 10, \"safety_risk\": 2, "
        "\"notes\": \"Issue resolved; patient privacy was fully protected.\"}. "
        "Returns a JSON parse error description if the model output is malformed."
    ),
    {"transcript": str},
)
async def analyze_call_outcome_tool(args):
    # print("  -> analyze_call_outcome called", flush=True)
    transcript = args.get("transcript", "").strip()
    if not transcript:
        return {"content": [{"type": "text", "text": json.dumps({
            "isError": True, "errorCategory": "validation", "isRetryable": False,
            "context": {"attempted": "analyze_call_outcome", "reason": "transcript input was empty or missing"},
        })}]}
    return {"content": [{"type": "text", "text": analyze_call_outcome(transcript)}]}


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
        model="claude-haiku-4-5-20251001",  # haiku is sufficient: call one tool, return result
        maxTurns=3,  # safety cap: stop retrying after 3 attempts
        description=(
            "QA reviewer responsible ONLY for the support agent's tone. "
            "Scores professionalism, empathy, and clarity. "
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
        model="claude-haiku-4-5-20251001",  # haiku is sufficient: call one tool, return result
        maxTurns=3,  # safety cap: stop retrying after 3 attempts
        description=(
            "QA reviewer responsible ONLY for the patient's tone. "
            "Scores respectfulness, clarity, and cooperation. "
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
        model="claude-haiku-4-5-20251001",  # haiku is sufficient: call one tool, return result
        maxTurns=3,  # safety cap: stop retrying after 3 attempts
        description=(
            "QA reviewer responsible for the overall call outcome and compliance. "
            "Scores whether the issue was resolved, next-step clarity, privacy handling, "
            "and safety risk across both parties."
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

def _get_tool_text(tool_response: Any) -> str:
    # The SDK delivers tool_response as a bare list of content items, not wrapped in a dict.
    if isinstance(tool_response, list):
        items = tool_response
    elif isinstance(tool_response, dict):
        items = tool_response.get("content") or []
    else:
        return ""
    parts = []
    for item in items:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text") or "")
    return "\n".join(parts).strip()

async def validate_tool_output(hook_input: dict[str, Any], *_: Any) -> dict[str, Any]:
    reviewer = TOOL_TO_REVIEWER.get(hook_input.get("tool_name"))
    if not reviewer:
        return {}

    # print(f"  [hook] {reviewer} hook_input keys: {list(hook_input.keys())}", flush=True)
    # print(f"  [hook] {reviewer} tool_response type: {type(hook_input.get('tool_response')).__name__}", flush=True)
    # print(f"  [hook] {reviewer} tool_response: {hook_input.get('tool_response')!r}", flush=True)
    raw_text = _get_tool_text(hook_input.get("tool_response"))
    # print(f"  [hook] {reviewer} extracted raw_text: {raw_text!r}", flush=True)

    try:
        data = json.loads(raw_text) if raw_text else None
    except json.JSONDecodeError as exc:
        return _hook_feedback(f"{reviewer} output was not valid JSON: {exc}")

    # Detect structured error returned by the tool (e.g. API failure, timeout).
    if isinstance(data, dict) and data.get("isError"):
        category = data.get("errorCategory", "unknown")
        retryable = data.get("isRetryable", False)
        context = data.get("context", {})
        retry_msg = "Retry the tool call once." if retryable else "Do not retry — escalate or skip this reviewer."
        return _hook_feedback(
            f"{reviewer} tool failed (errorCategory={category}, isRetryable={retryable}). "
            f"Context: {context}. {retry_msg}"
        )

    error = validate_reviewer(reviewer, data)
    if error:
        return _hook_feedback(f"{reviewer} JSON is invalid: {error}")

    return {}  # empty dict = accept the result, no feedback to the subagent

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
#Agent SDK structured output     → output_format=json_schema
#Messages API structured output  → forced tool_use

options = ClaudeAgentOptions(
    model="claude-haiku-4-5-20251001",  # pin coordinator; prevents SDK defaulting to claude-sonnet-4-6
    system_prompt=(
        "You coordinate hospital call QA. In one response, issue Task calls to "
        "agent_tone_reviewer, patient_tone_reviewer, and call_outcome_reviewer "
        "in parallel. Then return ONE final JSON object matching the required schema. "
        "Use the `transcript_id` given in the user prompt. "
        "If a reviewer fails, set that reviewer's field to null and record the error reason "
        "in reviewer_errors as {\"<reviewer_name>\": \"<reason>\"}."
    ),
    output_format={"type": "json_schema", "schema": JSON_SCHEMA},
    mcp_servers={"qa_tools": qa_server},
    agents=agents,  # passing agents= enables the SDK's built-in Task tool on the coordinator
    allowed_tools=["Task"],  # restrict coordinator to delegation only — no direct tool calls
    permission_mode="bypassPermissions",  # subagents call tools without interactive approval prompts
    hooks={
        "PostToolUse": [
            HookMatcher(
                matcher="|".join(TOOL_TO_REVIEWER.keys()),  # pipe-delimited OR-pattern across all three tool names
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
    async for message in query(prompt=prompt, options=options):# options contains the coordinator agent definition
        # print(f"\n[coordinator message] type={type(message).__name__} | {message}")
        if session_id is None:
            session_id = getattr(message, "session_id", None)
        # SDK populates structured_output (not text) when output_format=json_schema is set.
        candidate = getattr(message, "structured_output", None)
        if isinstance(candidate, dict):
            structured = candidate

    # print(f"Session ID: {session_id}")

    if structured is None:
        raise RuntimeError("Coordinator did not return a structured JSON result.")

    return structured


# Per-reviewer progress messages used by the streaming endpoint.
_REVIEWER_PROGRESS = {
    "mcp__qa_tools__analyze_agent_tone":
        "Agent tone reviewer analyzing professionalism, empathy, and clarity.",
    "mcp__qa_tools__analyze_patient_tone":
        "Patient tone reviewer analyzing respectfulness, clarity, and cooperation.",
    "mcp__qa_tools__analyze_call_outcome":
        "Call outcome reviewer checking issue resolution, next-step clarity, privacy handling, and safety risk.",
}


async def _run_coordinator_streamed(prompt: str):
    """
    Same pipeline as _run_coordinator, but yields real-time progress events.

    Yields ("progress", "<message>") whenever a real moment occurs in the
    SDK message stream, and finally ("result", <dict>) with the structured
    output. Detection is based on ToolUseBlock / ToolResultBlock content
    blocks the coordinator and reviewers emit while running.
    """
    structured = None
    dispatched = False                 # first Task tool_use seen
    started: set[str] = set()          # reviewer tools we've already announced
    completed: set[str] = set()        # reviewer tool_results we've already counted
    use_id_to_name: dict[str, str] = {}
    assembled = False

    async for message in query(prompt=prompt, options=options):
        # Both AssistantMessage and UserMessage carry content blocks we care about.
        if isinstance(message, (AssistantMessage, UserMessage)):
            content = message.content if isinstance(message.content, list) else []

            for block in content:
                # Tool calls: the coordinator dispatches Task → reviewer calls MCP tool.
                if isinstance(block, ToolUseBlock):
                    use_id_to_name[block.id] = block.name

                    if block.name == "Task" and not dispatched:
                        dispatched = True
                        yield ("progress", "Coordinator dispatching three specialist reviewers.")

                    if block.name in _REVIEWER_PROGRESS and block.name not in started:
                        started.add(block.name)
                        yield ("progress", _REVIEWER_PROGRESS[block.name])

                # Tool results: one fires per reviewer once the hook accepts the JSON.
                elif isinstance(block, ToolResultBlock):
                    name = use_id_to_name.get(block.tool_use_id)
                    if name in _REVIEWER_PROGRESS and name not in completed:
                        if not completed:
                            yield ("progress", "PostToolUse hook validating each reviewer JSON immediately.")
                        completed.add(name)
                        if len(completed) == 3:
                            yield ("progress", "Reviewer outputs passed schema checks.")

        # SDK delivers the final structured JSON via ResultMessage.structured_output.
        candidate = getattr(message, "structured_output", None)
        if isinstance(candidate, dict):
            structured = candidate
            if not assembled:
                assembled = True
                yield ("progress", "Coordinator assembling final structured report.")

    if structured is None:
        raise RuntimeError("Coordinator did not return a structured JSON result.")

    yield ("result", structured)


# 6. Process each transcript file.
async def process_transcript(file_path: Path) -> None:
    transcript = file_path.read_text(encoding="utf-8").strip() # mock_transcripts/*.txt
    if not transcript:
        print(f"{file_path.name}: skipped (empty file)")
        return

    print(f"\nProcessing {file_path.name}...", flush=True)

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
    parser = argparse.ArgumentParser(description="Run QA analysis on sample transcripts.")
    parser.add_argument("--case", help="Run one transcript by name, e.g. no_patient_speech")
    args = parser.parse_args()

    transcripts_dir = _BACKEND_ROOT / "mock_transcripts"
    if args.case:
        case_name = args.case if args.case.endswith(".txt") else f"{args.case}.txt"
        transcripts = [transcripts_dir / case_name]
    else:
        transcripts = sorted(transcripts_dir.glob("*.txt"))

    if not transcripts:
        raise RuntimeError("No transcripts found in backend/mock_transcripts/")

    for file_path in transcripts:
        if not file_path.is_file():
            raise FileNotFoundError(f"No transcript found at {file_path}")
        await process_transcript(file_path)


if __name__ == "__main__":
    asyncio.run(main())

