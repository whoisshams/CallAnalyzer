import json
import anthropic


def analyze_call_outcome(transcript: str) -> str:
    """
    Ask Claude to score the WHOLE CALL (resolution, next steps, escalation,
    PHI/compliance) and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=700,
            system=(
                "You are a hospital QA reviewer assessing the overall outcome of the entire call. "
                "Evaluate both the support agent and patient together to determine how the call concluded. "
                "Return ONLY a valid JSON object — no markdown, no code fences, no extra keys. "
                "Required fields and scoring rubric: "
                "resolution_completeness (int 1-10): how fully the patient's issue was resolved; "
                "1=unresolved and patient left worse off, 10=issue fully resolved to patient's satisfaction. "
                "next_step_clarity (int 1-10): how clearly any follow-up actions or next steps were communicated; "
                "1=no next steps given, 10=clear, specific, and confirmed next steps provided. "
                "phi_compliance (int 1-10): adherence to PHI/HIPAA rules during the call; "
                "1=clear PHI breach occurred, 5=PHI was mentioned but handled ambiguously, 10=no PHI at risk or all PHI handled correctly. "
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
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        return "".join(text_blocks).strip()

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
