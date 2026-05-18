# Author: Shams Anjum, 2026

"""
Quick checker for files in backend/output/.

For each saved JSON file we:
1. Load it with json.loads.
2. Run validate_report from schema.py.

Prints PASS or FAIL for each and exits non-zero if any FAIL.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from agent.schema import validate_report


def main() -> int:
    output_dir = _BACKEND_ROOT / "output"
    files = sorted(output_dir.glob("*.json"))
    if not files:
        print(f"No JSON files in {output_dir}")
        return 1

    failed = 0
    for file_path in files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL {file_path.name}: invalid JSON ({exc})")
            failed += 1
            continue

        error = validate_report(data)
        if error:
            print(f"FAIL {file_path.name}: {error}")
            failed += 1
        else:
            print(f"PASS {file_path.name}")

    if failed:
        print(f"\n{failed} file(s) failed validation.")
        return 1

    print("\nAll outputs are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
