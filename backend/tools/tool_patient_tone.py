# Author: Shams Anjum, 2026

import json
import anthropic

from tools.structured_output import build_score_submission_tool, extract_forced_tool_json


PATIENT_TONE_TOOL = build_score_submission_tool(
    "patient_tone_reviewer",
    "submit_patient_tone_scores",
    "Submit structured 1-10 scores and notes for the patient only.",
)



def analyze_patient_tone(transcript: str) -> str:
    """
    Ask Claude to score the PATIENT's tone and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=(
                "You are a hospital QA reviewer scoring ONLY the patient's behavior. "
                "Ignore anything the support agent says — do not let agent behavior influence patient scores. "
                "Score each dimension based solely on the patient's words, tone, and actions. "
                "Use the submit_patient_tone_scores tool to submit the final scores; do not answer in prose. "
                "Required fields and scoring rubric: "
                "respectfulness (int 1-10): politeness and courtesy toward the agent; "
                "1=abusive, threatening, or insulting language, 3=rude and dismissive but no explicit abuse, "
                "5=neutral in tone but occasionally impatient or blunt, 10=consistently respectful and polite. "
                "clarity (int 1-10): how clearly the patient communicated their issue or needs; "
                "1=incoherent or contradictory — the agent cannot understand the request, "
                "3=vague or incomplete — key details are missing, "
                "5=understandable but required the agent to ask follow-up questions, 10=clear and well-articulated from the start. "
                "cooperation (int 1-10): willingness to follow agent instructions and provide needed information; "
                "1=refused all agent requests, 3=resisted most requests but complied under pressure, "
                "5=partially cooperative — followed some instructions but resisted others, 10=fully cooperative throughout. "
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
            # Forced tool_use gives the inner model call a schema-bound output contract.
            tools=[PATIENT_TONE_TOOL],
            tool_choice={"type": "tool", "name": "submit_patient_tone_scores"},
        )
        return extract_forced_tool_json(response, "submit_patient_tone_scores")

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