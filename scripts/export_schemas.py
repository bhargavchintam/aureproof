# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Write the contracts' JSON Schemas to specs/contracts/v0.1/.

    uv run python scripts/export_schemas.py          # write
    uv run python scripts/export_schemas.py --check  # exit 1 if stale

tests/contracts/test_sarif_and_schemas.py fails when the committed schemas
drift from the models, so run this after changing a contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aureproof.contracts.schema import SCHEMA_DIR, export_schemas

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report drift, write nothing")
    args = parser.parse_args()

    out_dir = ROOT / SCHEMA_DIR
    wanted = {
        out_dir / f"{name}.schema.json": json.dumps(schema, indent=2, sort_keys=True) + "\n"
        for name, schema in export_schemas().items()
    }
    existing = set(out_dir.glob("*.schema.json")) if out_dir.exists() else set()
    stale = sorted(
        str(p.relative_to(ROOT))
        for p, text in wanted.items()
        if not p.exists() or p.read_text(encoding="utf-8") != text
    ) + sorted(str(p.relative_to(ROOT)) for p in existing - set(wanted))

    if args.check:
        for path in stale:
            print(f"stale: {path}")
        return 1 if stale else 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for path in existing - set(wanted):
        path.unlink()
    for path, text in wanted.items():
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(wanted)} schemas to {SCHEMA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
