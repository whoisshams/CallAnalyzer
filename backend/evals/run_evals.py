# Author: Shams Anjum, 2026

"""
Compare one cached QA report in backend/output/ against the expected
score ranges in backend/evals/cases/.

Usage:
    python3 backend/evals/run_evals.py bad_agent
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = Path(__file__).resolve().parent / "cases"
OUTPUT_DIR = _BACKEND_ROOT / "output"


def check_expected_ranges(report: dict, expected_ranges: dict) -> list[str]:
    """Return a list of failure messages for fields outside their expected range."""
    failures = []
    for reviewer, fields in expected_ranges.items():
        block = report.get(reviewer)
        if not isinstance(block, dict):
            failures.append(f"{reviewer} is missing or not an object")
            continue
        for field, score_range in fields.items():
            if score_range == []:
                continue
            min_score, max_score = score_range
            actual = block.get(field)
            if actual is None:
                failures.append(f"{reviewer}.{field} is missing")
            elif actual < min_score or actual > max_score:
                failures.append(f"{reviewer}.{field} = {actual}, expected {min_score}-{max_score}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare one cached QA report against its expected score ranges.")
    parser.add_argument("name", help="Case name, e.g. bad_agent (matches cases/<name>.json and output/<name>.json)")
    args = parser.parse_args()

    case_path = CASES_DIR / f"{args.name}.json"
    output_path = OUTPUT_DIR / f"{args.name}.json"

    if not case_path.is_file():
        print(f"Missing case file: {case_path}")
        return 1
    if not output_path.is_file():
        print(f"Missing output file: {output_path}. Run hub_spoke.py first.")
        return 1

    case = json.loads(case_path.read_text(encoding="utf-8"))
    report = json.loads(output_path.read_text(encoding="utf-8"))

    failures = check_expected_ranges(report, case.get("expected_ranges", {}))
    if failures:
        print(f"FAIL {args.name}")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"PASS {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
