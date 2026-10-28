# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""CLI validate / score --offline / report, the Phase-1 gate, and storage safety (issue #16)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from aureproof.bundle.canonical import canonical_json, digest_ref
from aureproof.bundle.run import EpisodeInput, labels_path, seal_run
from aureproof.cli.main import app
from aureproof.storage import BlobStore, StorageError, read_bundle, write_bundle

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL = ROOT / "examples" / "bundles" / "tutorial-v0.1"
GOLDEN = json.loads((ROOT / "conformance/scoring/v0.1/golden.json").read_text("utf-8"))
runner = CliRunner()


def _copy(tmp_path: Path) -> Path:
    dest = tmp_path / "bundle"
    shutil.copytree(TUTORIAL, dest)
    return dest


# ---- Phase-1 gate --------------------------------------------------------------------


def test_phase_1_gate_offline_rescore_matches_the_independent_calculation() -> None:
    """Golden cohort C-01 was calculated by hand before the matcher existed."""
    result = runner.invoke(app, ["score", str(TUTORIAL), "--offline", "--json"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out["status"] == "reproduced"
    expected = next(c for c in GOLDEN["cohorts"] if c["id"] == "C-01")["expected"]
    got = {
        name: {"numerator": m["numerator"], "denominator": m["denominator"]}
        for name, m in out["metrics"]["metrics"].items()
    }
    assert got == expected


def test_tutorial_bundle_is_committed_exactly_as_generated() -> None:
    spec = importlib.util.spec_from_file_location("tut", ROOT / "scripts/make_tutorial_bundle.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build() == read_bundle(TUTORIAL)


# ---- validate ------------------------------------------------------------------------


def test_validate_exit_codes(tmp_path: Path) -> None:
    assert runner.invoke(app, ["validate", str(TUTORIAL)]).exit_code == 0
    bundle = _copy(tmp_path)
    (bundle / "verdicts.json").write_text("[]")
    result = runner.invoke(app, ["validate", str(bundle)])
    assert result.exit_code == 1 and "INVALID" in result.output
    assert runner.invoke(app, ["validate", str(tmp_path / "missing")]).exit_code == 2


def test_trusted_seal_digest_is_checked(tmp_path: Path) -> None:
    seal = (TUTORIAL / "seal.intoto.json").read_bytes()
    good = runner.invoke(
        app, ["validate", str(TUTORIAL), "--trusted-seal-digest", digest_ref(seal)]
    )
    bad = runner.invoke(app, ["validate", str(TUTORIAL), "--trusted-seal-digest", digest_ref(b"x")])
    assert (good.exit_code, bad.exit_code) == (0, 1)


# ---- score ---------------------------------------------------------------------------


def test_score_requires_offline_and_a_valid_bundle(tmp_path: Path) -> None:
    assert runner.invoke(app, ["score", str(TUTORIAL)]).exit_code == 2
    bundle = _copy(tmp_path)
    (bundle / "metrics.json").write_text("{}")
    assert runner.invoke(app, ["score", str(bundle), "--offline"]).exit_code == 1


def _sealed(findings: list[Any], *, verdicts_override: bytes | None = None) -> dict[str, bytes]:
    labels = GOLDEN["label_sets"]["g1"]
    data = json.dumps(findings).encode()
    episode = EpisodeInput(
        episode_id="e1",
        task_id="g1",
        variant="vulnerable",
        labels=labels_path("g1"),
        agent_view=labels["agent_view"]["vulnerable"],
        signals={"evidence_complete": True, "runner_outcome": "ok"},
        submission=digest_ref(data),
    )
    return seal_run(
        [episode],
        {labels_path("g1"): canonical_json(labels)},
        [data],
        cohort="t",
        generator={"name": "aureproof", "version": "test"},
    )


def test_rescore_mismatch_is_reported(tmp_path: Path) -> None:
    """A correctly sealed bundle whose recorded verdicts disagree with the oracle."""
    from aureproof.bundle import Member, build_bundle
    from aureproof.bundle.models import Manifest

    files = _sealed(
        [
            {
                "cwe": 89,
                "locations": [{"file": "app/orders.py", "symbol": "find_orders"}],
                "description": "sqli",
            }
        ]
    )
    forged = json.loads(files["verdicts.json"])
    forged[0]["verdicts"][0]["verdict"] = "refuted"
    forged[0]["verdicts"][0]["rule"] = "M7"
    forged[0]["verdicts"][0].pop("defect_id")
    forged[0]["credited"] = []
    manifest = Manifest.model_validate_json(files["manifest.json"])
    members = [
        Member(
            m.path,
            canonical_json(forged) if m.path == "verdicts.json" else files[m.path],
            m.role,
            m.media_type,
        )
        for m in manifest.members
        if m.role not in ("journal", "blob")
    ]
    from aureproof.contracts import Event

    events = [
        Event.model_validate(json.loads(line)["event"])
        for line in files["journal.jsonl"].splitlines()
    ]
    blobs = [files[m.path] for m in manifest.members if m.role == "blob"]
    seal = json.loads(files["seal.intoto.json"])["predicate"]
    resealed = build_bundle(
        members, events, blobs=blobs, versions=seal["versions"], generator=seal["generator"]
    )
    write_bundle(resealed, tmp_path / "forged")
    result = runner.invoke(app, ["score", str(tmp_path / "forged"), "--offline"])
    assert result.exit_code == 1 and "mismatch" in result.output


# ---- report --------------------------------------------------------------------------

XSS = "<script>alert(1)</script><img src=x onerror=alert(2)>"


def test_html_report_escapes_agent_authored_strings(tmp_path: Path) -> None:
    files = _sealed(
        [
            {
                "cwe": 89,
                "description": XSS,
                "locations": [{"file": "app/orders.py", "symbol": "find_orders"}],
                "notes": "<b>x</b>",
            }
        ]
    )
    write_bundle(files, tmp_path / "xss")
    out = tmp_path / "report.html"
    result = runner.invoke(app, ["report", str(tmp_path / "xss"), "--out", str(out)])
    assert result.exit_code == 0, result.output
    html_text = out.read_text("utf-8")
    assert "<script>" not in html_text and "<img" not in html_text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_text
    assert "Content-Security-Policy" in html_text


def test_report_shows_denominators_outcomes_and_limitations(tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    result = runner.invoke(app, ["report", str(TUTORIAL), "--out", str(out), "--format", "md"])
    assert result.exit_code == 0, result.output
    text = out.read_text("utf-8")
    for needle in (
        "3/11",
        "3/4",
        "1/9",
        "Unsigned",
        "Completeness: complete",
        "No trusted seal digest",
        "controlled skills",
    ):
        assert needle in text, needle
    html_out = tmp_path / "report.html"
    runner.invoke(app, ["report", str(TUTORIAL), "--out", str(html_out)])
    html_text = html_out.read_text("utf-8")
    for disposition in (
        "safety_refusal",
        "infra_failure",
        "evidence_incomplete",
        "budget_exhausted",
    ):
        assert disposition in html_text


def test_report_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    out = tmp_path / "r.html"
    out.write_text("keep")
    assert runner.invoke(app, ["report", str(TUTORIAL), "--out", str(out)]).exit_code == 2
    assert out.read_text() == "keep"
    assert (
        runner.invoke(app, ["report", str(TUTORIAL), "--out", str(out), "--force"]).exit_code == 0
    )


def test_invalid_bundle_report_is_written_with_exit_1(tmp_path: Path) -> None:
    bundle = _copy(tmp_path)
    (bundle / "verdicts.json").write_text("[]")
    out = tmp_path / "r.md"
    result = runner.invoke(app, ["report", str(bundle), "--out", str(out), "--format", "md"])
    assert result.exit_code == 1 and "INVALID" in out.read_text("utf-8")


# ---- storage safety ------------------------------------------------------------------


def test_reader_rejects_symlinks_and_special_files(tmp_path: Path) -> None:
    bundle = _copy(tmp_path)
    (bundle / "extra.json").symlink_to(bundle / "metrics.json")
    with pytest.raises(StorageError, match="symlink"):
        read_bundle(bundle)
    (bundle / "extra.json").unlink()
    (bundle / "linkdir").symlink_to(bundle / "tasks", target_is_directory=True)
    with pytest.raises(StorageError, match="symlink"):
        read_bundle(bundle)
    (bundle / "linkdir").unlink()
    os.mkfifo(bundle / "fifo")
    with pytest.raises(StorageError, match="regular file"):
        read_bundle(bundle)
    (bundle / "fifo").unlink()
    with pytest.raises(StorageError, match="symlink"):
        link = tmp_path / "rootlink"
        link.symlink_to(bundle, target_is_directory=True)
        read_bundle(link)
    assert runner.invoke(app, ["validate", str(tmp_path / "rootlink")]).exit_code == 2


def test_reader_enforces_size_limit(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="larger"):
        read_bundle(TUTORIAL, max_bytes=100)


def test_writer_is_atomic_and_never_overwrites(tmp_path: Path) -> None:
    files = read_bundle(TUTORIAL)
    target = tmp_path / "out"
    write_bundle(files, target)
    assert read_bundle(target) == files
    with pytest.raises(StorageError, match="exists"):
        write_bundle(files, target)
    with pytest.raises(StorageError, match="non-canonical"):
        write_bundle({**files, "../escape": b"x"}, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()
    assert not [p for p in tmp_path.iterdir() if ".tmp-" in p.name]


def test_content_addressed_store(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "cas")
    ref = store.put(b"hello")
    assert ref == digest_ref(b"hello") and store.get(ref) == b"hello"
    assert store.put(b"hello") == ref  # idempotent
    path = tmp_path / "cas" / "sha256" / ref.removeprefix("sha256:")
    path.write_bytes(b"tampered")
    with pytest.raises(StorageError, match="does not match"):
        store.get(ref)
    with pytest.raises(StorageError, match="not a sha256"):
        store.get("sha256:../../etc/passwd")
