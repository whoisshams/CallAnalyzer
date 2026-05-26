# Author: Shams Anjum, 2026

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
    ],
    "patient_tone_reviewer": [
        "respectfulness",
        "clarity",
        "cooperation",
    ],
    "call_outcome_reviewer": [
        "issue_resolved",
        "next_step_clarity",
        "privacy_handling",
        "safety_risk",
    ],
}  

# validate_reviewer checks if the reviewer block is valid
def validate_reviewer(reviewer_key, payload):
    """Check one reviewer block."""
    if reviewer_key not in REVIEWER_FIELDS:
        return f"unknown reviewer '{reviewer_key}'"
    
    if not isinstance(payload, dict):
        return f"{reviewer_key} must be a JSON object"

    for field in REVIEWER_FIELDS[reviewer_key]:
        if field not in payload:
            return f"{reviewer_key}.{field} is missing"

        value = payload[field]
        # bool is a subclass of int in Python, so True/False would pass the isinstance(int) check below without this guard.
        if isinstance(value, bool):
            return f"{reviewer_key}.{field} must be an integer from 1 to 10"
        if not isinstance(value, int):
            return f"{reviewer_key}.{field} must be an integer from 1 to 10"
        if value < 1 or value > 10:
            return f"{reviewer_key}.{field} must be an integer from 1 to 10"
    # notes is validated separately because it follows different rules (non-empty string, not a scored int).
    if "notes" not in payload:
        return f"{reviewer_key}.notes is missing"

    notes = payload["notes"]

    if not isinstance(notes, str):
        return f"{reviewer_key}.notes must be a non-empty string"
    if not notes.strip():
        return f"{reviewer_key}.notes must be a non-empty string"

    return None

# data is a dictionary containing the final report
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
        if data[reviewer_key] is None:
            continue  # reviewer failed — null is acceptable
        error = validate_reviewer(reviewer_key, data[reviewer_key])
        if error:
            return error

    return None
# build_reviewer_schema builds the JSON schema for one reviewer block
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
        "oneOf": [
            {
                "type": "object",
                "required": required_fields,
                "properties": properties,
                "additionalProperties": False,
            },
            {"type": "null"},
        ]
    }

# Passed to the coordinator's output_format; enforces additionalProperties=False so the model can't add undeclared fields.
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
        "reviewer_errors": {
            "type": "object",
            "description": "Present only when one or more reviewers failed.",
        },
    },
    "additionalProperties": False,
}
