# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Export the gate examples' bundles as Every Eval Ever 0.3.0 records (issue #59).

    uv run python scripts/make_eee_examples.py            # write
    uv run python scripts/make_eee_examples.py --check    # exit 1 on drift

The records go under ``examples/eee/data/<benchmark>/<developer>/<model>/<uuid>.json``,
the layout EEE's own validator expects. The CI job "EEE consumer" validates them
with the pinned ``every-eval-ever`` package, which is the independent consumer.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from aureproof.exporters.eee import to_eee
from aureproof.storage import read_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "eee"
TIMESTAMP = "1793232000"  # 2026-10-28T00:00:00Z, fixed so the examples are reproducible
SOURCES = [("pass", "a"), ("pass", "b")]


def build() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for example, side in SOURCES:
        bundle = read_bundle(ROOT / "examples" / "gate" / example / side)
        record = to_eee(bundle, retrieved_timestamp=TIMESTAMP, organization="Aureproof examples")
        model = record.record["model_info"]["id"]
        name = uuid.uuid5(uuid.NAMESPACE_URL, record.record["evaluation_id"])
        path = f"data/aureproof-security/{model}/{name}.json"
        files[path] = (json.dumps(record.record, indent=2) + "\n").encode()
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build()
    on_disk = (
        {p.relative_to(OUT).as_posix(): p.read_bytes() for p in OUT.rglob("*.json") if p.is_file()}
        if OUT.exists()
        else {}
    )
    if args.check:
        if on_disk != files:
            print("examples/eee drifted: run scripts/make_eee_examples.py", file=sys.stderr)
            return 1
        print(f"examples/eee: {len(files)} files match")
        return 0
    for path, data in files.items():
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f"wrote {len(files)} files under {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
