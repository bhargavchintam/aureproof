# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Generate the Evidence Bundle conformance vectors (specs/bundle/README.md §8).

    uv run python scripts/make_bundle_vectors.py

One valid bundle, plus invalid variants that each apply a single mutation. The
output is deterministic, and tests/bundle/test_bundle.py fails if the committed
vectors drift from this script.
"""

from __future__ import annotations

import base64
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aureproof.bundle import Member, build_bundle, canonical_json, digest_ref
from aureproof.contracts import Event

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "bundle" / "v0.1"
BLOB = (
    b'[{"cwe": 862, "locations": [{"file": "docstore/service.py", '
    b'"symbol": "delete_document"}], "description": "No ownership check."}]\n'
)
VERSIONS = {
    "matcher": "0.1.0",
    "disposition": "0.1.0",
    "metrics": "0.1.0",
    "contracts": "0.1",
    "scoring_spec": "0.1",
}
Files = dict[str, bytes]


def _event(seq: int, kind: str, **extra: Any) -> Event:
    return Event.model_validate(
        {
            "seq": seq,
            "episode_id": "authz-001:vulnerable:r0",
            "actor": "runner",
            "kind": kind,
            "observation_source": "controller_observed",
            **extra,
        }
    )


def base_bundle() -> Files:
    events = [
        _event(0, "episode_planned"),
        _event(1, "episode_dispatched", attempt_id="a0"),
        _event(2, "submission_captured", attempt_id="a0", blob_refs=[digest_ref(BLOB)]),
        _event(
            3, "episode_scored", attempt_id="a0", payload={"disposition": "completed_with_findings"}
        ),
    ]
    verdicts = [
        {
            "finding_index": 0,
            "verdict": "confirmed",
            "rule": "M1",
            "defect_id": "authz-001-d1",
            "matcher_version": "0.1.0",
        }
    ]
    metrics = [
        {
            "metric": "strict_confirmed_yield",
            "kind": "proportion",
            "numerator": 1,
            "denominator": 1,
            "value": 1.0,
            "metric_version": "0.1.0",
        }
    ]
    members = [
        Member("verdicts.json", canonical_json(verdicts), "verdicts"),
        Member("metrics.json", canonical_json(metrics), "metrics"),
        Member("system/reference.json", canonical_json({"subject": "scripted"}), "system"),
    ]
    return build_bundle(
        members,
        events,
        blobs=[BLOB],
        versions=VERSIONS,
        generator={"name": "aureproof", "version": "vectors"},
    )


def _journal_lines(files: Files) -> list[bytes]:
    return files["journal.jsonl"].splitlines(keepends=True)


def _with(files: Files, **changes: bytes | None) -> Files:
    out = dict(files)
    for path, data in changes.items():
        path = path.replace("__", "/").replace("_DOT_", ".")
        if data is None:
            out.pop(path)
        else:
            out[path] = data
    return out


def _flip(data: bytes, index: int = -3) -> bytes:
    b = bytearray(data)
    b[index] ^= 0x01
    return bytes(b)


def _seal_with(files: Files, **predicate: Any) -> bytes:
    seal = json.loads(files["seal.intoto.json"])
    seal["predicate"].update(predicate)
    return canonical_json(seal)


MUTATIONS: dict[str, tuple[str, list[str], Callable[[Files], Files]]] = {
    "tampered-member": (
        "One byte of verdicts.json changed after sealing.",
        ["V2"],
        lambda f: {**f, "verdicts.json": _flip(f["verdicts.json"])},
    ),
    "truncated-journal": (
        "Last journal entry removed (tail truncation).",
        ["V2", "V3"],
        lambda f: {**f, "journal.jsonl": b"".join(_journal_lines(f)[:-1])},
    ),
    "reordered-journal": (
        "Two journal entries swapped.",
        ["V2", "V3"],
        lambda f: {
            **f,
            "journal.jsonl": b"".join(
                [_journal_lines(f)[1], _journal_lines(f)[0], *_journal_lines(f)[2:]]
            ),
        },
    ),
    "edited-event": (
        "An event payload edited in place, hash left as it was.",
        ["V2", "V3"],
        lambda f: {
            **f,
            "journal.jsonl": f["journal.jsonl"].replace(
                b"completed_with_findings", b"completed_no_findings"
            ),
        },
    ),
    "missing-mandatory-member": (
        "metrics.json removed.",
        ["V2", "V4"],
        lambda f: {k: v for k, v in f.items() if k != "metrics.json"},
    ),
    "missing-journal": (
        "journal.jsonl removed.",
        ["V1", "V2", "V3", "V4"],
        lambda f: {k: v for k, v in f.items() if k != "journal.jsonl"},
    ),
    "unlisted-file": (
        "A file the manifest does not list.",
        ["V2"],
        lambda f: {**f, "notes.txt": b"added after sealing\n"},
    ),
    "noncanonical-manifest": (
        "manifest.json pretty-printed (same JSON value).",
        ["V1", "V6"],
        lambda f: {
            **f,
            "manifest.json": json.dumps(json.loads(f["manifest.json"]), indent=2).encode(),
        },
    ),
    "seal-count-mismatch": (
        "Seal claims one more event than the journal holds.",
        ["V3"],
        lambda f: {
            **f,
            "seal.intoto.json": _seal_with(
                f, event_count=json.loads(f["seal.intoto.json"])["predicate"]["event_count"] + 1
            ),
        },
    ),
    "forged-seal-subject": (
        "Seal subject digest does not match manifest.json.",
        ["V6"],
        lambda f: {
            **f,
            "seal.intoto.json": canonical_json(
                {
                    **json.loads(f["seal.intoto.json"]),
                    "subject": [{"name": "manifest.json", "digest": {"sha256": "0" * 64}}],
                }
            ),
        },
    ),
    "blob-misnamed": (
        "A blob whose content does not match its digest path.",
        ["V2"],
        lambda f: {**f, **{k: v + b" " for k, v in f.items() if k.startswith("blobs/")}},
    ),
    "missing-seal": (
        "seal.intoto.json removed.",
        ["V1"],
        lambda f: {k: v for k, v in f.items() if k != "seal.intoto.json"},
    ),
    "path-traversal": (
        "A member path that leaves the bundle.",
        ["V1", "V2"],
        lambda f: {**f, "../escape.json": b"{}"},
    ),
}


def _encode(files: Files) -> dict[str, str]:
    return {p: base64.b64encode(files[p]).decode() for p in sorted(files)}


def vectors() -> dict[str, dict[str, Any]]:
    base = base_bundle()
    out: dict[str, dict[str, Any]] = {
        "valid/minimal": {
            "description": "A sealed, unsigned bundle with a 4-event journal and one blob.",
            "expected_failed_checks": [],
            "files": _encode(base),
        }
    }
    for name, (description, failed, mutate) in MUTATIONS.items():
        out[f"invalid/{name}"] = {
            "description": description,
            "expected_failed_checks": failed,
            "files": _encode(mutate(base)),
        }
    return out


def main() -> int:
    for key, vector in vectors().items():
        path = OUT / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(vector, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(vectors())} vectors to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
