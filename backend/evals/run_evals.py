# Author: Shams Anjum, 2026

"""
Compare cached QA reports in backend/output/ against expected score ranges
in backend/evals/cases/.

Usage:
    python3 backend/evals/run_evals.py bad_agent     # one case
    python3 backend/evals/run_evals.py --all         # all cases
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = Path(__file__).resolve().parent / "cases"
OUTPUT_DIR = _BACKEND_ROOT / "output"


def check_expected_ranges(report: dict, expected_ranges: dict) -> tuple[list[str], int, int]:
    """Return (failure messages, fields_checked, fields_passed)."""
    failures = []
    checked = 0
    passed = 0
    for reviewer, fields in expected_ranges.items():
        block = report.get(reviewer)
        if not isinstance(block, dict):
            failures.append(f"{reviewer} is missing or not an object")
            continue
        for field, score_range in fields.items():
            if score_range == []:
                continue
            checked += 1
            min_score, max_score = score_range
            actual = block.get(field)
            if actual is None:
                failures.append(f"{reviewer}.{field} is missing")
            elif actual < min_score or actual > max_score:
                failures.append(f"{reviewer}.{field} = {actual}, expected {min_score}-{max_score}")
            else:
                passed += 1
    return failures, checked, passed


def eval_one(name: str) -> tuple[bool, int, int]:
    """Check one case. Returns (passed, fields_checked, fields_passed)."""
    case_path = CASES_DIR / f"{name}.json"
    output_path = OUTPUT_DIR / f"{name}.json"

    if not case_path.is_file():
        print(f"FAIL {name}\n  - missing case file: {case_path.name}")
        return False, 0, 0
    if not output_path.is_file():
        print(f"FAIL {name}\n  - missing output file: {output_path.name}; run hub_spoke.py first")
        return False, 0, 0

    case = json.loads(case_path.read_text(encoding="utf-8"))
    report = json.loads(output_path.read_text(encoding="utf-8"))

    failures, checked, passed = check_expected_ranges(report, case.get("expected_ranges", {}))
    if failures:
        print(f"FAIL {name}")
        for failure in failures:
            print(f"  - {failure}")
        return False, checked, passed

    print(f"PASS {name}")
    return True, checked, passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare cached QA reports against expected score ranges.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("name", nargs="?", help="Case name, e.g. bad_agent")
    group.add_argument("--all", action="store_true", help="Run all cases in evals/cases/")
    args = parser.parse_args()

    if args.all:
        names = sorted(p.stem for p in CASES_DIR.glob("*.json"))
        if not names:
            print(f"No eval cases found in {CASES_DIR}")
            return 1
        outcomes = [eval_one(name) for name in names]
        cases_passed = sum(1 for ok, _, _ in outcomes if ok)
        total_checked = sum(c for _, c, _ in outcomes)
        total_passed  = sum(p for _, _, p in outcomes)
        total_failed  = total_checked - total_passed
        field_rate = total_passed / total_checked * 100 if total_checked else 0
        print(
            f"Field-level pass rate: {total_passed}/{total_checked} fields ({field_rate:.2f}%)\n"
            f"{total_failed} field{'s' if total_failed != 1 else ''} out of range"
        )
        return 0 if cases_passed == len(outcomes) else 1

    ok, checked, passed = eval_one(args.name)
    if checked:
        field_rate = passed / checked * 100
        print(f"\nField-level pass rate: {passed}/{checked} fields ({field_rate:.2f}%)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
