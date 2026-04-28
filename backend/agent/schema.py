"""
This file describes the final QA report format.

It does two jobs:
1. It lists the fields each reviewer must return.
2. It checks whether a final report follows that structure.

If a report is valid, the validator returns None.
If a report is invalid, the validator returns a short error message.

The code here is intentionally simple and explicit.
"""


# REVIEWER_FIELDS maps each reviewer name to the list of score fields
# that reviewer must return.
REVIEWER_FIELDS = {
    "agent_tone_reviewer": [
        "professionalism",
        "empathy",
        "clarity",
        "helpfulness",
        "de_escalation",
    ],
    "patient_tone_reviewer": [
        "respectfulness",
        "clarity",
        "cooperation",
        "emotional_regulation",
        "escalation_intensity",
    ],
    "call_outcome_reviewer": [
        "resolution_completeness",
        "next_step_clarity",
        "phi_compliance",
        "safety_risk",
        "escalation_necessity",
    ],
}


# the parameters are of any type
def validate_reviewer(reviewer_key, payload):
    """Check one reviewer block."""
    if reviewer_key not in REVIEWER_FIELDS:
        return f"unknown reviewer '{reviewer_key}'"
    
    #checks if the payload is a dictionary
    if not isinstance(payload, dict):
        return f"{reviewer_key} must be a JSON object"

    # this is for the fields in the reviewer_key
    for field in REVIEWER_FIELDS[reviewer_key]:
        if field not in payload:
            return f"{reviewer_key}.{field} is missing"

        value = payload[field]
        #checks if the value is a boolean
        if isinstance(value, bool):
            return f"{reviewer_key}.{field} must be an integer from 1 to 10"
        #checks if the value is an integer
        if not isinstance(value, int):
            return f"{reviewer_key}.{field} must be an integer from 1 to 10"
        #checks if the value is between 1 and 10
        if value < 1 or value > 10:
            return f"{reviewer_key}.{field} must be an integer from 1 to 10"
    # this is for the notes field. It is separate because it 
    # follows different validation rules than the other fields.
    if "notes" not in payload:
        return f"{reviewer_key}.notes is missing"

    notes = payload["notes"]

    if not isinstance(notes, str):
        return f"{reviewer_key}.notes must be a non-empty string"
    #checks if the notes is a non-empty string
    if not notes.strip():
        return f"{reviewer_key}.notes must be a non-empty string"

    return None


def validate_report(data):
    """Check the full final report."""
    if not isinstance(data, dict):
        return "report must be a JSON object"

    required_top_level_fields = [
        "transcript_id",
        "agent_tone_reviewer",
        "patient_tone_reviewer",
        "call_outcome_reviewer",
        "coordinator_summary",
    ]

    for field_name in required_top_level_fields:
        if field_name not in data:
            return f"{field_name} is missing"

    transcript_id = data["transcript_id"]
    if not isinstance(transcript_id, str) or not transcript_id.strip():
        return "transcript_id must be a non-empty string"

    coordinator_summary = data["coordinator_summary"]
    if not isinstance(coordinator_summary, str) or not coordinator_summary.strip():
        return "coordinator_summary must be a non-empty string"

    for reviewer_key in REVIEWER_FIELDS:
        error = validate_reviewer(reviewer_key, data[reviewer_key])
        if error:
            return error

    return None

# this is for the reviewer_key
def build_reviewer_schema(reviewer_key):
    """Build the JSON schema for one reviewer block."""
    fields = REVIEWER_FIELDS[reviewer_key]

    required_fields = []
    for field in fields:
        required_fields.append(field)
    required_fields.append("notes")

    properties = {}
    for field in fields:
        properties[field] = {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
        }

    properties["notes"] = {"type": "string"}

    return {
        "type": "object",
        "required": required_fields,
        "properties": properties,
        "additionalProperties": False,
    }

# this is for the JSON schema used by the coordinator's `output_format`.
# It tells the model what the final JSON should look like.
JSON_SCHEMA = {
    "type": "object",
    "required": [
        "transcript_id",
        "agent_tone_reviewer",
        "patient_tone_reviewer",
        "call_outcome_reviewer",
        "coordinator_summary",
    ],
    "properties": {
        "transcript_id": {"type": "string"},
        "agent_tone_reviewer": build_reviewer_schema("agent_tone_reviewer"),
        "patient_tone_reviewer": build_reviewer_schema("patient_tone_reviewer"),
        "call_outcome_reviewer": build_reviewer_schema("call_outcome_reviewer"),
        "coordinator_summary": {"type": "string"},
    },
    "additionalProperties": False,
}
