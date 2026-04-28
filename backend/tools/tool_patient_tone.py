from anthropic import Anthropic


def analyze_patient_tone(transcript: str) -> str:
    """
    Ask Claude to score the PATIENT's tone and return a JSON string.
    Validation happens later in the PostToolUse hook.
    """
    client = Anthropic()
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
            "1=highly dysregulated or volatile, 10=calm and composed throughout. "
            "escalation_intensity (int 1-10): degree to which the patient escalated tension; "
            "1=no escalation at all, 10=extreme escalation. "
            "notes (non-empty string): one sentence summarizing the patient's overall behavior. "
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