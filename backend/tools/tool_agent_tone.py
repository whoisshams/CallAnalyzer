# Author: Shams Anjum, 2026

import json
import anthropic

from tools.structured_output import build_score_submission_tool, extract_forced_tool_json


AGENT_TONE_TOOL = build_score_submission_tool(
    "agent_tone_reviewer",
    "submit_agent_tone_scores",
    "Submit structured 1-10 scores and notes for the support agent only.",
)


def analyze_agent_tone(transcript: str) -> str:
    """
    Ask Claude to score the SUPPORT AGENT's tone and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=(
                "You are a hospital QA reviewer scoring ONLY the support agent's behavior. "
                "Ignore anything the patient says — do not let patient behavior influence agent scores. "
                "Score each dimension based solely on the agent's words, tone, and actions. "
                "Use the submit_agent_tone_scores tool to submit the final scores; do not answer in prose. "
                "Required fields and scoring rubric: "
                "professionalism (int 1-10): adherence to professional language and standards; "
                "1=hostile or abusive language used, 3=dismissive or curt responses with no hostile language, "
                "5=neutral and transactional — polite but minimal effort, 10=exemplary professional conduct throughout. "
                "empathy (int 1-10): acknowledgment of patient feelings and concerns; "
                "1=completely dismissive of patient distress, 3=acknowledged once but did not follow through, "
                "5=showed some understanding but moved on quickly without validating feelings, 10=highly compassionate and validating throughout. "
                "clarity (int 1-10): how clearly the agent communicated information and instructions; "
                "1=confusing or contradictory, 3=responded but gave only dismissals with no actionable content (e.g. 'try again later', 'not my problem'), "
                "5=communicated the gist but left key details vague, 10=perfectly clear and structured. "
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
            # Forced tool_use gives the inner model call a schema-bound output contract.
            tools=[AGENT_TONE_TOOL],
            tool_choice={"type": "tool", "name": "submit_agent_tone_scores"},
        )

        return extract_forced_tool_json(response, "submit_agent_tone_scores")
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

