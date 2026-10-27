# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Write the JSON Schemas for contracts (specs/contracts/v0.1) and bundle records
(specs/bundle/v0.1).

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

from aureproof.bundle import schema as bundle_schema
from aureproof.contracts import schema as contract_schema
from aureproof.contracts import thr_schema

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report drift, write nothing")
    args = parser.parse_args()

    wanted: dict[Path, str] = {}
    existing: set[Path] = set()
    for module in (contract_schema, bundle_schema, thr_schema):
        out_dir = ROOT / module.SCHEMA_DIR
        existing |= set(out_dir.glob("*.schema.json")) if out_dir.exists() else set()
        for name, schema in module.export_schemas().items():
            wanted[out_dir / f"{name}.schema.json"] = (
                json.dumps(schema, indent=2, sort_keys=True) + "\n"
            )
    stale = sorted(
        str(p.relative_to(ROOT))
        for p, text in wanted.items()
        if not p.exists() or p.read_text(encoding="utf-8") != text
    ) + sorted(str(p.relative_to(ROOT)) for p in existing - set(wanted))

    if args.check:
        for path in stale:
            print(f"stale: {path}")
        return 1 if stale else 0

    for path in existing - set(wanted):
        path.unlink()
    for path, text in wanted.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(wanted)} schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
