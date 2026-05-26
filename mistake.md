# Bug Post-Mortem: `PostToolUse` Hook Always Extracting Empty Text

**File affected:** `backend/agent/hub_spoke.py`
**Function affected:** `_get_tool_text`
**Date discovered:** May 2, 2026

---

## Summary

The `PostToolUse` hook responsible for validating reviewer JSON outputs was silently discarding every tool response because it assumed the wrong data shape for the `tool_response` argument. As a result, every tool call was falsely flagged as returning invalid JSON, causing retry loops, wasted API calls, and in one case (`bad_agent.txt`) all three reviewer fields being set to `null` in the output.

---

## Background

The system uses a hub-and-spoke multi-agent setup. A coordinator agent dispatches to three subagent reviewers via the Claude Agent SDK. Each subagent calls one MCP tool (`analyze_agent_tone`, `analyze_patient_tone`, `analyze_call_outcome`) and returns a JSON block with integer scores.

A `PostToolUse` hook (`validate_tool_output`) runs after each tool call to validate the returned JSON against the expected schema. If valid, it returns `{}` (accept). If invalid, it returns feedback instructing the subagent to retry.

The helper `_get_tool_text` was responsible for extracting the raw JSON string from the tool response object before parsing it.

---

## The Bug

### Incorrect assumption about `tool_response` shape

The `_get_tool_text` function was written assuming the SDK delivers `tool_response` as a **dict** in MCP envelope format:

```python
{"content": [{"type": "text", "text": "{...json...}"}]}
```

So the guard on line 2 of the function exited early for anything that wasn't a dict:

```python
# BUGGY VERSION
def _get_tool_text(tool_response: Any) -> str:
    # MCP tool responses wrap content in {"content": [{"type": "text", "text": "..."}]}.
    if not isinstance(tool_response, dict):   # <-- exits here for every actual response
        return ""
    parts = []
    for item in tool_response.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text") or "")
    return "\n".join(parts).strip()
```

### What the SDK actually delivers

The Claude Agent SDK passes `tool_response` to the hook as a **bare list** of content items — the inner array directly, without the outer `{"content": ...}` wrapper:

```python
# Actual value received at runtime
[{'type': 'text', 'text': '{\n  "professionalism": 2,\n  "empathy": 1, ...}'}]
```

Terminal debug output confirmed this:

```
[hook] agent_tone_reviewer tool_response type: list
[hook] agent_tone_reviewer tool_response: [{'type': 'text', 'text': '{\n  "professionalism": 2, ...}'}]
[hook] agent_tone_reviewer extracted raw_text: ''   ← always empty
```

Because `isinstance(list, dict)` is `False`, the guard fired and returned `""` on every single call without ever iterating the content.

---

## Cascade of Failures

With `raw_text` always `""`, the rest of the hook logic followed this path:

```python
# raw_text = "" → data = None
data = json.loads(raw_text) if raw_text else None

# validate_reviewer("agent_tone_reviewer", None) returns:
# "agent_tone_reviewer must be a JSON object"  ← None is not a dict
error = validate_reviewer(reviewer, data)
if error:
    return _hook_feedback(f"{reviewer} JSON is invalid: {error}")
```

`_hook_feedback` returned a retry instruction to the subagent for every tool call, even when the tool had returned a perfectly valid JSON response.

### Observed symptoms per transcript

| Transcript | Symptom | Root cause |
|---|---|---|
| `bad_agent.txt` | All three reviewers set to `null` in output; `reviewer_errors` populated | Subagents obeyed hook's "retry" feedback, eventually hit `maxTurns=3` cap and gave up. Coordinator saw all reviewers as failed. |
| `bad_patient.txt` | Output was correct | Subagents happened to ignore the hook feedback and returned the JSON they already had from the tool result. Non-deterministic model behavior. |
| `smooth_call.txt` | Each tool called 4–5 times instead of once; significant token waste | Subagents kept retrying per the hook's false feedback before the coordinator eventually assembled a valid result. |

The `bad_agent.txt` output before the fix:

```json
{
  "transcript_id": "bad_agent.txt",
  "agent_tone_reviewer": null,
  "patient_tone_reviewer": null,
  "call_outcome_reviewer": null,
  "coordinator_summary": "Call analysis failed: All three reviewers encountered JSON validation errors...",
  "reviewer_errors": {
    "agent_tone_reviewer": "JSON validation failed - system reported invalid JSON object despite returned structure appearing correct",
    "patient_tone_reviewer": "JSON validation failed - system reported invalid JSON object despite returned structure appearing correct",
    "call_outcome_reviewer": "JSON validation failed - system reported invalid JSON object despite returned structure appearing correct"
  }
}
```

Notably, the coordinator's own summary said *"despite returned structure appearing correct"* — the model itself could tell something was wrong with the validation.

---

## The Fix

Handle both the list shape (what the SDK actually delivers) and the dict shape (the originally assumed format) defensively:

```python
# FIXED VERSION
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
```

After the fix, terminal output confirmed correct extraction:

```
[hook] agent_tone_reviewer tool_response type: list
[hook] agent_tone_reviewer extracted raw_text: '{"professionalism": 2, "empathy": 1, ...}'
```

And `bad_agent.json` after the fix produced real scores:

```json
{
  "transcript_id": "bad_agent.txt",
  "agent_tone_reviewer": {
    "professionalism": 2,
    "empathy": 1,
    "clarity": 3,
    "notes": "Agent was dismissive, rude, and unhelpful throughout the call..."
  },
  ...
}
```

---

## Lesson

**Never assume an SDK's internal data shape matches its documented envelope format.** When writing hook or middleware code that inspects SDK-internal objects, always log the actual runtime type and value first (as the debug prints here did), and write the extraction logic to handle what you observe — not what you expect based on documentation or the tool's own return format.

When in doubt, make the extraction function defensive against multiple shapes rather than hard-failing on the first unexpected type.
