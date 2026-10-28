# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Build the offline tutorial bundle from golden cohort C-01 (issue #16).

    uv run python scripts/make_tutorial_bundle.py            # write
    uv run python scripts/make_tutorial_bundle.py --check    # exit 1 on drift

C-01's metric counts were calculated independently (by hand and by a separate
implementation) before the matcher existed. Re-scoring this bundle offline must
reproduce them exactly: that is the Phase-1 gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aureproof.bundle.canonical import canonical_json, digest_ref
from aureproof.bundle.run import EpisodeInput, labels_path, seal_run

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "conformance" / "scoring" / "v0.1" / "golden.json"
OUT = ROOT / "examples" / "bundles" / "tutorial-v0.1"


def _submission(sub: dict[str, Any]) -> bytes | None:
    if sub.get("absent"):
        return None
    if "raw" in sub:
        return str(sub["raw"]).encode()
    if "repeat" in sub:
        return json.dumps([sub["repeat"]["finding"]] * sub["repeat"]["count"]).encode()
    return json.dumps(sub["findings"]).encode()


def build() -> dict[str, bytes]:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    cohort = next(c for c in golden["cohorts"] if c["id"] == "C-01")
    cases = {c["id"]: c for c in golden["cases"]}
    labels = golden["label_sets"]["g1"]
    episodes, submissions = [], []
    for case_id in cohort["episodes"]:
        case = cases[case_id]
        data = _submission(case["submission"])
        if data is not None:
            submissions.append(data)
        episodes.append(
            EpisodeInput(
                episode_id=case_id,
                task_id="g1",
                variant=case["variant"],
                labels=labels_path("g1"),
                agent_view=labels["agent_view"][case["variant"]],
                signals=case["signals"],
                submission=None if data is None else digest_ref(data),
            )
        )
    return seal_run(
        episodes,
        {labels_path("g1"): canonical_json(labels)},
        submissions,
        cohort="C-01",
        generator={"name": "aureproof", "version": "tutorial"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build()
    on_disk = (
        {p.relative_to(OUT).as_posix(): p.read_bytes() for p in OUT.rglob("*") if p.is_file()}
        if OUT.exists()
        else {}
    )
    if args.check:
        stale = sorted(set(files) ^ set(on_disk)) + sorted(
            k for k in files if k in on_disk and files[k] != on_disk[k]
        )
        for path in stale:
            print(f"stale: {path}")
        return 1 if stale else 0
    for path in set(on_disk) - set(files):
        (OUT / path).unlink()
    for path, data in files.items():
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f"wrote {len(files)} files to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
