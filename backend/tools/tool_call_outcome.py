from anthropic import Anthropic


def analyze_call_outcome(transcript: str) -> str:
    """
    Ask Claude to score the WHOLE CALL (resolution, next steps, escalation,
    PHI/compliance) and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = Anthropic()
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
            "score 10 if no PHI was at risk or all PHI was handled correctly, "
            "1=clear PHI breach occurred. "
            "safety_risk (int 1-10): degree of patient safety concern raised during the call; "
            "1=no safety concern at all, 10=immediate life-threatening risk identified. "
            "escalation_necessity (int 1-10): how necessary it was to escalate this call; "
            "1=no escalation needed, 10=immediate escalation to a supervisor or emergency service was required. "
            "notes (non-empty string): one sentence summarizing the overall call outcome. "
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
