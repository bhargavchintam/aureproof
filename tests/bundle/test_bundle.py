# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Evidence Bundle v0.1 (specs/bundle/README.md, issue #13)."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aureproof.bundle import (
    GENESIS,
    BundleError,
    Member,
    build_bundle,
    canonical_json,
    digest_ref,
    validate,
)
from aureproof.contracts import Event

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "conformance" / "bundle" / "v0.1"
VERSIONS = {
    "matcher": "0.1.0",
    "disposition": "0.1.0",
    "metrics": "0.1.0",
    "contracts": "0.1",
    "scoring_spec": "0.1",
}
BLOB = b"captured findings.json bytes"


def _event(seq: int, **extra: Any) -> Event:
    return Event.model_validate(
        {
            "seq": seq,
            "episode_id": "ep-1",
            "actor": "runner",
            "kind": "step",
            "observation_source": "controller_observed",
            **extra,
        }
    )


def _members() -> list[Member]:
    return [
        Member(path="verdicts.json", data=canonical_json([]), role="verdicts"),
        Member(path="metrics.json", data=canonical_json({}), role="metrics"),
        Member(path="system/subject.json", data=canonical_json({"name": "s"}), role="system"),
    ]


def _bundle(events: int = 3) -> dict[str, bytes]:
    evs = [_event(i) for i in range(events)]
    if events:
        evs[-1] = _event(events - 1, blob_refs=[digest_ref(BLOB)])
    return build_bundle(
        _members(),
        evs,
        blobs=[BLOB] if events else [],
        versions=VERSIONS,
        generator={"name": "aureproof", "version": "test"},
    )


def test_rfc8785_example() -> None:
    """RFC 8785 §3.2.2's example: numbers, strings and key order canonicalize exactly."""
    rfc_input = r"""{
        "numbers": [333333333.33333329, 1E30, 4.50, 2e-3, 0.000000000000000000000000001],
        "string": "\u20ac$\u000F\u000aA'\u0042\u0022\u005c\\\"\/",
        "literals": [null, true, false]}"""
    rfc_output = r"""{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],"string":"€$\u000f\nA'B\"\\\\\"/"}"""  # noqa: E501
    assert canonical_json(json.loads(rfc_input)) == rfc_output.encode()


def test_digest_ignores_key_order() -> None:
    assert digest_ref({"a": 1, "b": 2}) == digest_ref({"b": 2, "a": 1})
    assert digest_ref(b"x").startswith("sha256:") and len(digest_ref(b"x")) == 71


def test_valid_bundle_passes_every_check_except_unsigned() -> None:
    report = validate(_bundle())
    assert report.valid, report.problems()
    statuses = {c.id: c.status for c in report.checks}
    assert statuses == {
        "V1": "pass",
        "V2": "pass",
        "V3": "pass",
        "V4": "pass",
        "V5": "skipped",
        "V6": "pass",
    }


def test_build_is_deterministic() -> None:
    assert _bundle() == _bundle()


def test_empty_journal_seals_genesis() -> None:
    files = _bundle(events=0)
    seal = json.loads(files["seal.intoto.json"])
    assert seal["predicate"]["event_count"] == 0
    assert seal["predicate"]["journal_head"] == GENESIS
    assert files["journal.jsonl"] == b""
    assert validate(files).valid


def test_seal_is_an_in_toto_statement_over_the_manifest() -> None:
    files = _bundle()
    seal = json.loads(files["seal.intoto.json"])
    assert seal["_type"] == "https://in-toto.io/Statement/v1"
    assert seal["subject"] == [
        {"name": "manifest.json", "digest": {"sha256": digest_ref(files["manifest.json"])[7:]}}
    ]
    assert seal["predicate"]["event_count"] == 3


@pytest.mark.parametrize("missing", ["verdicts", "metrics"])
def test_builder_refuses_missing_mandatory_evidence(missing: str) -> None:
    members = [m for m in _members() if m.role != missing]
    with pytest.raises(BundleError, match=missing):
        build_bundle(
            members, [], blobs=[], versions=VERSIONS, generator={"name": "a", "version": "0"}
        )


def test_builder_refuses_unresolved_blob_refs_and_reserved_paths() -> None:
    with pytest.raises(BundleError, match="blob"):
        build_bundle(
            _members(),
            [_event(0, blob_refs=[digest_ref(b"nope")])],
            blobs=[],
            versions=VERSIONS,
            generator={"name": "a", "version": "0"},
        )
    with pytest.raises(BundleError, match="reserved"):
        build_bundle(
            [*_members(), Member(path="manifest.json", data=b"{}", role="other")],
            [],
            blobs=[],
            versions=VERSIONS,
            generator={"name": "a", "version": "0"},
        )
    with pytest.raises(BundleError, match="seq"):
        build_bundle(
            _members(),
            [_event(1)],
            blobs=[],
            versions=VERSIONS,
            generator={"name": "a", "version": "0"},
        )


def _load_vector(path: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    vector = json.loads(path.read_text(encoding="utf-8"))
    files = {p: base64.b64decode(b) for p, b in vector["files"].items()}
    return files, vector


VECTOR_FILES = sorted(VECTORS.glob("*/*.json"))


@pytest.mark.parametrize("path", VECTOR_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_conformance_vector(path: Path) -> None:
    files, vector = _load_vector(path)
    report = validate(files)
    failed = sorted(c.id for c in report.checks if c.status == "fail")
    assert report.valid == (path.parent.name == "valid")
    assert failed == vector["expected_failed_checks"], report.problems()


def test_vectors_cover_the_definition_of_done() -> None:
    names = {p.stem for p in VECTOR_FILES}
    assert {"tampered-member", "truncated-journal", "missing-mandatory-member"} <= names
    assert len([p for p in VECTOR_FILES if p.parent.name == "invalid"]) >= 10


def test_committed_vectors_match_the_generator() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "make_vectors", ROOT / "scripts" / "make_bundle_vectors.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generated = module.vectors()
    on_disk = {
        f"{p.parent.name}/{p.stem}": json.loads(p.read_text(encoding="utf-8")) for p in VECTOR_FILES
    }
    assert on_disk == generated


@settings(max_examples=100, deadline=None)
@given(st.integers(1, 8), st.data())
def test_any_single_byte_change_is_detected(n: int, data: st.DataObject) -> None:
    """Every byte is tamper-evident given a trusted seal digest (spec §1, V6).

    Without one, only the seal's own metadata (generator, versions,
    completeness) can change undetected: nothing inside a bundle can
    authenticate its trust root. Every other file is always covered.
    """
    files = _bundle(n)
    path = data.draw(st.sampled_from(sorted(files)))
    if not files[path]:
        return
    i = data.draw(st.integers(0, len(files[path]) - 1))
    mutated = bytearray(files[path])
    mutated[i] ^= data.draw(st.integers(1, 255))
    tampered = {**files, path: bytes(mutated)}
    trusted = digest_ref(files["seal.intoto.json"])
    assert not validate(tampered, trusted_seal_digest=trusted).valid
    if path != "seal.intoto.json":
        assert not validate(tampered).valid


def test_seal_metadata_needs_the_trusted_digest() -> None:
    files = _bundle()
    edited = files["seal.intoto.json"].replace(b'"name":"aureproof"', b'"name":"attacker"')
    assert edited != files["seal.intoto.json"]
    tampered = {**files, "seal.intoto.json": edited}
    assert validate(tampered).valid  # documented limit of an unsigned seal
    report = validate(tampered, trusted_seal_digest=digest_ref(files["seal.intoto.json"]))
    assert [c.id for c in report.checks if c.status == "fail"] == ["V6"]


@settings(max_examples=40, deadline=None)
@given(st.integers(2, 10), st.data())
def test_any_journal_truncation_is_detected(n: int, data: st.DataObject) -> None:
    files = _bundle(n)
    lines = files["journal.jsonl"].splitlines(keepends=True)
    keep = data.draw(st.integers(0, len(lines) - 1))
    truncated = b"".join(lines[:keep])
    report = validate({**files, "journal.jsonl": truncated})
    assert "V3" in {c.id for c in report.checks if c.status == "fail"}
