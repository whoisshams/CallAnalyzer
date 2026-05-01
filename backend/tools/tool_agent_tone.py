import json
import anthropic


def analyze_agent_tone(transcript: str) -> str:
    """
    Ask Claude to score the SUPPORT AGENT's tone and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=700,
            system=(
                "You are a hospital QA reviewer scoring ONLY the support agent's behavior. "
                "Ignore anything the patient says — do not let patient behavior influence agent scores. "
                "Score each dimension based solely on the agent's words, tone, and actions. "
                "Return ONLY a valid JSON object — no markdown, no code fences, no extra keys. "
                "Required fields and scoring rubric: "
                "professionalism (int 1-10): adherence to professional language and standards; "
                "1=rude or inappropriate, 10=exemplary professional conduct. "
                "empathy (int 1-10): acknowledgment of patient feelings and concerns; "
                "1=dismissive, 10=highly compassionate and validating. "
                "clarity (int 1-10): how clearly the agent communicated information and instructions; "
                "1=confusing or contradictory, 10=perfectly clear and structured. "
                "helpfulness (int 1-10): how effectively the agent addressed the patient's needs; "
                "1=unhelpful or incorrect, 10=fully resolved the issue. "
                "de_escalation (int 1-10): ability to calm tension; "
                "1=made situation worse, 5=no tension present or tension unchanged, 10=fully de-escalated. "
                "notes (string, 10-30 words): one sentence citing the single most significant outcome or unresolved issue from the call. "
                "If the agent has no dialogue in the transcript, score all fields 1 and set "
                "notes to 'No agent speech found.'"
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
    # API failures (rate limit, timeout, auth)
    except anthropic.AuthenticationError:
        return json.dumps({"isError": True, "errorCategory": "auth", "isRetryable": False,
                           "context": {"attempted": "analyze_agent_tone", "reason": "Invalid or missing API key"}})
    except anthropic.RateLimitError:
        return json.dumps({"isError": True, "errorCategory": "rate_limit", "isRetryable": True,
                           "context": {"attempted": "analyze_agent_tone", "suggestion": "Retry after a short delay"}})
    except (anthropic.APITimeoutError, anthropic.APIConnectionError):
        return json.dumps({"isError": True, "errorCategory": "timeout", "isRetryable": True,
                           "context": {"attempted": "analyze_agent_tone", "suggestion": "Retry the tool call"}})
    except anthropic.APIError as exc:
        return json.dumps({"isError": True, "errorCategory": "api_error", "isRetryable": False,
                           "context": {"attempted": "analyze_agent_tone", "reason": str(exc)}})
