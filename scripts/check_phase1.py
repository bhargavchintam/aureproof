# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Phase-1 gate against an *installed* aureproof (issue #37).

    aureproof score examples/bundles/tutorial-v0.1 --offline --json > out.json
    python scripts/check_phase1.py out.json

Compares the re-scored counts with golden cohort C-01, which was calculated
independently. Uses only the standard library, so it runs in any fresh venv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(path: str) -> int:
    out = json.loads(Path(path).read_text(encoding="utf-8"))
    golden = json.loads((ROOT / "conformance/scoring/v0.1/golden.json").read_text(encoding="utf-8"))
    expected = next(c for c in golden["cohorts"] if c["id"] == "C-01")["expected"]
    got = {
        name: {"numerator": m["numerator"], "denominator": m["denominator"]}
        for name, m in out["metrics"]["metrics"].items()
    }
    if out.get("status") != "reproduced" or got != expected:
        print(f"PHASE-1 GATE FAILED: status={out.get('status')}")
        for name in sorted(set(expected) | set(got)):
            if expected.get(name) != got.get(name):
                print(f"  {name}: expected {expected.get(name)}, got {got.get(name)}")
        return 1
    print(f"Phase-1 gate passed: {len(got)} metrics equal golden cohort C-01")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
