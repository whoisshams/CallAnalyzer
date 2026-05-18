# Author: Shams Anjum, 2026

import json
from typing import Any

from agent.schema import REVIEWER_FIELDS

# "agent_tone_reviewer", "patient_tone_reviewer", "call_outcome_reviewer" are the reviewer keys in the REVIEWER_FIELDS dictionary.
def build_score_submission_tool(reviewer_key: str, tool_name: str, description: str) -> dict[str, Any]:
    """Create the forced tool_use schema for one reviewer payload."""
    properties = {
        field: {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
        }
        for field in REVIEWER_FIELDS[reviewer_key]
    }
    properties["notes"] = {"type": "string", "minLength": 1}

    return {
        "name": tool_name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": [*REVIEWER_FIELDS[reviewer_key], "notes"],
            "additionalProperties": False,
        },
    }


def extract_forced_tool_json(response: Any, tool_name: str) -> str:
    """Return the forced tool_use input as JSON text for the existing hook pipeline."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return json.dumps(getattr(block, "input", {}))

    return "{}"
