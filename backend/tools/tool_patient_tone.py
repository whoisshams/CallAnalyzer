import json
import anthropic


def analyze_patient_tone(transcript: str) -> str:
    """
    Ask Claude to score the PATIENT's tone and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=700,
            system=(
                "You are a hospital QA reviewer scoring ONLY the patient's behavior. "
                "Ignore anything the support agent says — do not let agent behavior influence patient scores. "
                "Score each dimension based solely on the patient's words, tone, and actions. "
                "Return ONLY a valid JSON object — no markdown, no code fences, no extra keys. "
                "Required fields and scoring rubric: "
                "respectfulness (int 1-10): politeness and courtesy toward the agent; "
                "1=abusive or hostile, 10=consistently respectful. "
                "clarity (int 1-10): how clearly the patient communicated their issue or needs; "
                "1=incoherent or contradictory, 10=clear and well-articulated. "
                "cooperation (int 1-10): willingness to follow agent instructions and provide needed information; "
                "1=completely uncooperative, 10=fully cooperative. "
                "emotional_regulation (int 1-10): ability to manage emotions during the call; "
                "1=highly dysregulated or volatile, 5=occasional emotional outbursts but mostly manageable, 10=calm and composed throughout. "
                "escalation_intensity (int 1-10): degree to which the patient escalated tension; "
                "1=no escalation at all, 5=repeated complaints or raised voice but no threats, 10=extreme escalation. "
                "notes (string, 10-30 words): one sentence citing the single most significant outcome or unresolved issue from the call. "
                "If the patient has no dialogue in the transcript, score all fields 1 and set "
                "notes to 'No patient speech found.'"
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
                           "context": {"attempted": "analyze_patient_tone", "reason": "Invalid or missing API key"}})
    except anthropic.RateLimitError:
        return json.dumps({"isError": True, "errorCategory": "rate_limit", "isRetryable": True,
                           "context": {"attempted": "analyze_patient_tone", "suggestion": "Retry after a short delay"}})
    except (anthropic.APITimeoutError, anthropic.APIConnectionError):
        return json.dumps({"isError": True, "errorCategory": "timeout", "isRetryable": True,
                           "context": {"attempted": "analyze_patient_tone", "suggestion": "Retry the tool call"}})
    except anthropic.APIError as exc:
        return json.dumps({"isError": True, "errorCategory": "api_error", "isRetryable": False,
                           "context": {"attempted": "analyze_patient_tone", "reason": str(exc)}})