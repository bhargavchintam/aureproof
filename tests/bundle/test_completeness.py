# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Incomplete evidence never seals as complete (scoring D1, bundle spec §6)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from aureproof.bundle import BundleError, validate
from aureproof.bundle.build import Member, build_bundle
from aureproof.bundle.models import MANIFEST, SEAL
from aureproof.bundle.public import redact
from aureproof.bundle.run import rescore
from aureproof.storage import read_bundle

ROOT = Path(__file__).resolve().parents[2]
COMPLETE = ROOT / "examples" / "gate" / "pass" / "a"


def _tutorial_module() -> Any:
    spec = importlib.util.spec_from_file_location("tut", ROOT / "scripts/make_tutorial_bundle.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _predicate(files: dict[str, bytes]) -> dict[str, Any]:
    predicate: dict[str, Any] = json.loads(files[SEAL])["predicate"]
    return predicate


def test_a_run_with_an_evidence_incomplete_episode_seals_as_incomplete() -> None:
    files = _tutorial_module().build()  # golden cohort C-01 has one such episode
    assert _predicate(files)["completeness"] == "incomplete"
    assert validate(files).valid  # honest and intact; completeness is reported, not hidden
    assert rescore(files).status == "reproduced"


def test_a_run_without_one_seals_as_complete() -> None:
    files = read_bundle(COMPLETE)
    assert _predicate(files)["completeness"] == "complete"
    assert rescore(files).status == "reproduced"


def test_a_bundle_claiming_complete_over_incomplete_evidence_does_not_reproduce() -> None:
    module = _tutorial_module()
    files = module.build()
    manifest = json.loads(files[MANIFEST])
    events = [json.loads(line)["event"] for line in files["journal.jsonl"].splitlines()]
    from aureproof.contracts import Event

    members = [
        Member(m["path"], files[m["path"]], m["role"], m["media_type"], m["mandatory"])
        for m in manifest["members"]
        if m["role"] not in ("journal", "blob")
    ]
    blobs = [v for k, v in sorted(files.items()) if k.startswith("blobs/")]
    predicate = _predicate(files)
    forged = build_bundle(
        members,
        [Event.model_validate(e) for e in events],
        blobs=blobs,
        versions=predicate["versions"],
        generator=predicate["generator"],
        completeness="complete",
    )
    redo = rescore(forged)
    assert redo.status == "mismatch"
    assert any("sealed as complete" in p for p in redo.problems)


def test_an_incomplete_run_cannot_become_a_public_bundle() -> None:
    module = _tutorial_module()
    with pytest.raises(BundleError, match="complete run"):
        redact(module.build())
