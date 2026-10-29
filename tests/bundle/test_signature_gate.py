# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Signed-evidence gate and public (redacted) bundles; pure core (issue #46)."""

from __future__ import annotations

from pathlib import Path

from aureproof.bundle import validate
from aureproof.bundle.public import public_problems, redact, secret_findings
from aureproof.bundle.run import rescore
from aureproof.bundle.validate import SignatureCheck
from aureproof.storage import read_bundle

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL = {
    k: v
    for k, v in read_bundle(ROOT / "examples/bundles/tutorial-v0.1").items()
    if k != "seal.sigstore.json"
}
# Public bundles are made only from complete runs; the tutorial is sealed as incomplete.
COMPLETE = read_bundle(ROOT / "examples/gate/pass/a")


def _v5(report: object) -> str:
    return next(c.status for c in report.checks if c.id == "V5")  # type: ignore[attr-defined]


def test_unsigned_is_valid_but_never_signed() -> None:
    report = validate(TUTORIAL)
    assert report.valid and not report.signed and _v5(report) == "skipped"


def test_signature_result_drives_v5_and_stays_distinct_from_validity() -> None:
    good = validate(TUTORIAL, signature=SignatureCheck(verified=True, identity="id", issuer="iss"))
    assert good.valid and good.signed and _v5(good) == "pass"
    bad = validate(TUTORIAL, signature=SignatureCheck(verified=False, problems=("wrong identity",)))
    assert not bad.valid and not bad.signed and _v5(bad) == "fail"
    assert "wrong identity" in " ".join(bad.problems())


def test_a_present_but_unverified_signature_is_only_skipped() -> None:
    report = validate({**TUTORIAL, "seal.sigstore.json": b"{}"})
    assert report.valid and not report.signed
    assert any("present but not verified" in p for p in report.problems())


def test_private_bundle_is_not_publishable() -> None:
    problems = public_problems(TUTORIAL)
    assert any("completeness" in p for p in problems)
    assert any("labels present" in p for p in problems)


def test_redaction_reseals_without_labels_and_cannot_be_rescored() -> None:
    public = redact(COMPLETE)
    assert validate(public).valid
    assert public_problems(public) == []
    assert not [p for p in public if p.endswith("/labels.json")]
    assert rescore(public).status == "not_rescorable"


def test_secret_scan_names_the_kind_never_the_secret() -> None:
    planted = "sk-ant-api03-" + "x" * 40
    hits = secret_findings({"episodes.json": planted.encode(), "ok.json": b"{}"})
    assert hits == ["episodes.json: anthropic_key"]
    assert planted not in " ".join(hits)
    leaky = {**redact(COMPLETE), "notes.txt": b"AKIA" + b"A" * 16}
    assert any("aws_access_key" in p for p in public_problems(leaky))
