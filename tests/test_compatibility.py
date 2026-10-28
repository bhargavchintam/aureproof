# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Readers fail closed on unknown versions (specs/COMPATIBILITY.md, issue #37)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aureproof.bundle import validate
from aureproof.bundle.canonical import canonical_json
from aureproof.contracts.decision import DecisionProtocol
from aureproof.contracts.thr import TaskHealthRecord
from aureproof.scoring import V0_1, UnregisteredParams, scoring_identity
from aureproof.storage import read_bundle

ROOT = Path(__file__).resolve().parents[1]
TUTORIAL = ROOT / "examples" / "bundles" / "tutorial-v0.1"


def _vector(path: str) -> dict[str, object]:
    return dict(json.loads((ROOT / path).read_text("utf-8"))["instance"])


def test_unknown_bundle_version_fails_validation() -> None:
    files = read_bundle(TUTORIAL)
    manifest = json.loads(files["manifest.json"])
    manifest["bundle_version"] = "0.2"
    report = validate({**files, "manifest.json": canonical_json(manifest)})
    assert not report.valid
    assert any("manifest.json does not match the schema" in p for p in report.problems())


def test_unknown_predicate_type_fails_validation() -> None:
    files = read_bundle(TUTORIAL)
    seal = json.loads(files["seal.intoto.json"])
    seal["predicateType"] = "https://example.invalid/predicate/v9"
    assert not validate({**files, "seal.intoto.json": canonical_json(seal)}).valid


def test_unknown_thr_version_is_rejected() -> None:
    record = _vector("conformance/thr/v0.1/valid/healthy.json")
    record["thr_version"] = "0.2"
    with pytest.raises(ValidationError, match="thr_version"):
        TaskHealthRecord.model_validate(record)


def test_unknown_protocol_version_is_rejected() -> None:
    vectors = json.loads((ROOT / "conformance/decision/v0.1/vectors.json").read_text("utf-8"))
    protocol = dict(vectors["cases"][0]["protocol"])
    protocol["protocol_version"] = "0.2"
    with pytest.raises(ValidationError, match="protocol_version"):
        DecisionProtocol.model_validate(protocol)


def test_unregistered_matcher_semantics_are_rejected() -> None:
    with pytest.raises(UnregisteredParams):
        scoring_identity(dataclasses.replace(V0_1, max_findings=257))
