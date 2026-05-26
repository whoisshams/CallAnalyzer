# Author: Shams Anjum, 2026

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
                "issue_resolved (int 1-10): how fully the patient's issue was resolved on this call; "
                "1=unresolved and patient left worse off, 3=issue unresolved but patient was given a reason or acknowledgment, "
                "5=issue partially addressed — a workaround or interim step was offered but the core problem remains, "
                "8=issue resolved but patient expressed some dissatisfaction with how, 10=issue fully resolved to patient's satisfaction. "
                "next_step_clarity (int 1-10): how clearly any next steps or follow-up actions were communicated; "
                "1=no next steps given at all, 3=a vague direction was mentioned but not explained, "
                "5=a next step was given but not confirmed or fully understood by the patient, "
                "10=clear, specific, and confirmed next steps provided and understood by the patient. "
                "privacy_handling (int 1-10): how well patient private information was protected during the call; "
                "1=patient data was clearly exposed or shared without consent, "
                "3=private information was disclosed despite patient objection, "
                "5=private information was mentioned but handled ambiguously, "
                "10=no PHI was at risk OR all PHI was handled correctly. "
                "If no patient-identifiable information was mentioned during the call, score 10 — absence of exposure is full compliance. "
                "safety_risk (int 1-10): degree of patient safety concern raised during the call; "
                "1=no safety concern mentioned, 3=patient mentions discomfort or mild symptoms only, "
                "5=patient reports pain, missed medication, or worsening condition, "
                "8=patient describes symptoms that may require urgent attention, 10=immediate life-threatening risk identified. "
                "notes (string, 10-30 words): one sentence citing the single most significant outcome or unresolved issue from the call. "
                "If there is no patient response, do not automatically score all fields 1. "
                "Score issue_resolved low because no patient issue was identified or resolved. "
                "Score next_step_clarity based on whether the agent gave a clear callback or follow-up instruction. "
                "Score privacy_handling according to PHI exposure; if no PHI was mentioned, score 10. "
                "Score safety_risk low unless symptoms or urgent risk are mentioned."
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
