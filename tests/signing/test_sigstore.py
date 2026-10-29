# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Offline Sigstore verification (issue #46). Needs the `sign` extra; no network.

The tutorial bundle's seal.sigstore.json was produced by the sign.yml workflow on
main, which is the project's only signer identity.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("sigstore")

from typer.testing import CliRunner

from aureproof.cli.main import app
from aureproof.signing import EXPECTED_IDENTITY, verify_bundle, verify_bytes
from aureproof.storage import read_bundle

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL = ROOT / "examples" / "bundles" / "tutorial-v0.1"
SIGNED = (TUTORIAL / "seal.sigstore.json").exists()
needs_signature = pytest.mark.skipif(
    not SIGNED, reason="tutorial bundle not yet signed by sign.yml"
)
runner = CliRunner()


def test_garbage_or_missing_signatures_are_rejected() -> None:
    files = {k: v for k, v in read_bundle(TUTORIAL).items() if k != "seal.sigstore.json"}
    assert not verify_bundle(files).verified
    assert "unsigned" in verify_bundle(files).problems[0]
    bad = verify_bytes(b"data", b'{"not": "a sigstore bundle"}')
    assert not bad.verified and bad.problems


@needs_signature
def test_workflow_signature_verifies_offline_with_the_expected_identity() -> None:
    check = verify_bundle(read_bundle(TUTORIAL))
    assert check.verified, check.problems
    assert check.identity == EXPECTED_IDENTITY


@needs_signature
def test_altered_bytes_and_wrong_identity_are_rejected() -> None:
    files = read_bundle(TUTORIAL)
    seal = files["seal.intoto.json"]
    assert not verify_bytes(seal + b" ", files["seal.sigstore.json"]).verified
    wrong = verify_bundle(files, identity=EXPECTED_IDENTITY.replace("sign.yml", "release.yml"))
    assert not wrong.verified


@needs_signature
def test_signed_evidence_gate_through_the_cli(tmp_path: Path) -> None:
    ok = runner.invoke(app, ["validate", str(TUTORIAL), "--require-signature"])
    assert ok.exit_code == 0, ok.output
    assert "V5 signature" in ok.output and "verified" in ok.output
    copy = tmp_path / "b"
    shutil.copytree(TUTORIAL, copy)
    (copy / "seal.sigstore.json").unlink()
    gate = runner.invoke(app, ["validate", str(copy), "--require-signature"])
    assert gate.exit_code == 1 and "signed-evidence gate" in gate.output
    assert runner.invoke(app, ["verify", str(TUTORIAL)]).exit_code == 0


@pytest.mark.skip(
    reason="re-signing: the completeness change re-sealed the tutorial; sign.yml runs on main "
    "after merge and the follow-up PR restores this check"
)
def test_the_tutorial_bundle_is_signed() -> None:
    """From #46 on, the signature is required evidence, not an optional extra."""
    assert SIGNED, "examples/bundles/tutorial-v0.1/seal.sigstore.json is missing"
