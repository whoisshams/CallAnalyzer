import json
import anthropic

from tools.structured_output import build_score_submission_tool, extract_forced_tool_json


CALL_OUTCOME_TOOL = build_score_submission_tool(
    "call_outcome_reviewer",
    "submit_call_outcome_scores",
    "Submit structured 1-10 scores and notes for the overall call outcome.",
)


def analyze_call_outcome(transcript: str) -> str:
    """
    Ask Claude to score the WHOLE CALL (resolution, next steps, escalation,
    PHI/compliance) and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=(
                "You are a hospital QA reviewer assessing the overall outcome of the entire call. "
                "Evaluate both the support agent and patient together to determine how the call concluded. "
                "Use the submit_call_outcome_scores tool to submit the final scores; do not answer in prose. "
                "Required fields and scoring rubric: "
                "resolution_completeness (int 1-10): how fully the patient's issue was resolved; "
                "1=unresolved and patient left worse off, 10=issue fully resolved to patient's satisfaction. "
                "followup_clarity (int 1-10): how clearly any follow-up actions were communicated; "
                "1=no follow-up steps given at all, 10=clear, specific, and confirmed next steps provided and understood by the patient. "
                "privacy_handling (int 1-10): how well patient private information was protected during the call; "
                "1=private patient information was clearly exposed or mishandled, 5=private information was mentioned but handled ambiguously, 10=no private information was at risk or all private information was handled correctly. "
                "safety_risk (int 1-10): degree of patient safety concern raised during the call; "
                "1=no safety concern at all, 5=patient reports pain or inability to take medication, 10=immediate life-threatening risk identified. "
                "escalation_necessity (int 1-10): how necessary it was to escalate this call; "
                "1=no escalation needed, 5=escalation would have improved outcome but was not critical, 10=immediate escalation to a supervisor or emergency service was required. "
                "notes (string, 10-30 words): one sentence citing the single most significant outcome or unresolved issue from the call. "
                "If the transcript contains no meaningful dialogue, score all fields 1 and set "
                "notes to 'No meaningful call content found.'"
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Transcript:\n{transcript}",
                }
            ],
            # Forced tool_use gives the inner model call a schema-bound output contract.
            tools=[CALL_OUTCOME_TOOL],
            tool_choice={"type": "tool", "name": "submit_call_outcome_scores"},
        )
        return extract_forced_tool_json(response, "submit_call_outcome_scores")

    except anthropic.AuthenticationError:
        return json.dumps({"isError": True, "errorCategory": "auth", "isRetryable": False,
                           "context": {"attempted": "analyze_call_outcome", "reason": "Invalid or missing API key"}})
    except anthropic.RateLimitError:
        return json.dumps({"isError": True, "errorCategory": "rate_limit", "isRetryable": True,
                           "context": {"attempted": "analyze_call_outcome", "suggestion": "Retry after a short delay"}})
    except (anthropic.APITimeoutError, anthropic.APIConnectionError):
        return json.dumps({"isError": True, "errorCategory": "timeout", "isRetryable": True,
                           "context": {"attempted": "analyze_call_outcome", "suggestion": "Retry the tool call"}})
    except anthropic.APIError as exc:
        return json.dumps({"isError": True, "errorCategory": "api_error", "isRetryable": False,
                           "context": {"attempted": "analyze_call_outcome", "reason": str(exc)}})
