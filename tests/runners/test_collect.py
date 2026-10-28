# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Bounded artifact collection (issue #40).

Runs the exact COLLECTOR script the Inspect adapter executes in the sandbox,
against hostile workspaces, then follows the result through scoring.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aureproof.contracts import EpisodeSignals, LabelSet, RunnerOutcome
from aureproof.runners.collect import ARTIFACT, COLLECT_LIMIT, COLLECTOR, Capture, interpret
from aureproof.scoring import score_episode

ROOT = Path(__file__).resolve().parents[2]
LABELS = LabelSet.model_validate_json(
    (ROOT / "fixtures/oracles/authz-001/labels.json").read_text("utf-8")
)
OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)


def collect(ws: Path, name: str = ARTIFACT, limit: int = COLLECT_LIMIT) -> Capture:
    out = subprocess.run(
        [sys.executable, "-c", COLLECTOR, str(ws), name, str(limit)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return interpret(out.stdout, limit=limit)


def test_regular_file_is_captured_byte_exact(tmp_path: Path) -> None:
    (tmp_path / ARTIFACT).write_bytes(b"[]\n")
    cap = collect(tmp_path)
    assert (cap.status, cap.data) == ("captured", b"[]\n")


def test_absent_file(tmp_path: Path) -> None:
    assert collect(tmp_path).status == "absent"


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        (lambda ws: (ws / ARTIFACT).symlink_to("/dev/zero"), "symlink"),
        (lambda ws: (ws / ARTIFACT).symlink_to(ws / "missing"), "symlink"),
        (lambda ws: (ws / ARTIFACT).symlink_to("/etc/hosts"), "symlink"),
        (lambda ws: os.mkfifo(ws / ARTIFACT), "not_regular_file"),
        (lambda ws: (ws / ARTIFACT).mkdir(), "not_regular_file"),
        (lambda ws: (ws / ARTIFACT).write_bytes(b"x" * 101), "oversized"),
    ],
    ids=["dev-zero", "dangling", "outside-file", "fifo", "directory", "oversized"],
)
def test_hostile_artifacts_are_rejected_without_unbounded_reads(
    tmp_path: Path, setup: object, reason: str
) -> None:
    setup(tmp_path)  # type: ignore[operator]
    cap = collect(tmp_path, limit=100)
    assert (cap.status, cap.reason, cap.data) == ("rejected", reason, None)


def test_exactly_at_the_limit_is_captured(tmp_path: Path) -> None:
    (tmp_path / ARTIFACT).write_bytes(b"[" + b" " * 98 + b"]")
    assert collect(tmp_path, limit=100).status == "captured"


@pytest.mark.parametrize("name", ["../findings.json", "/etc/passwd", "a/findings.json", ".."])
def test_names_cannot_escape_the_workspace(tmp_path: Path, name: str) -> None:
    cap = collect(tmp_path, name=name)
    assert (cap.status, cap.reason) == ("rejected", "bad_name")


def test_a_symlinked_workspace_root_is_resolved_before_checks(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ARTIFACT).write_bytes(b"[]")
    ws = tmp_path / "ws"
    ws.symlink_to(outside, target_is_directory=True)
    # The workspace root itself resolves; the artifact is a regular file inside it.
    assert collect(ws).status == "captured"


@pytest.mark.parametrize(
    "stdout",
    [
        "not json",
        json.dumps({"status": "captured", "b64": "AAAA", "sha256": "0" * 64}),
        json.dumps({"status": "captured", "b64": "@@@", "sha256": "0" * 64}),
        "x" * (4 * 100 + 1),
    ],
    ids=["garbage", "digest-mismatch", "bad-base64", "huge-output"],
)
def test_host_distrusts_the_collector_report(stdout: str) -> None:
    assert interpret(stdout, limit=100).status == "rejected"


def test_deep_or_numerous_findings_are_collected_then_rejected_as_invalid_output(
    tmp_path: Path,
) -> None:
    deep = b"[" * 40 + b"]" * 40
    many = json.dumps(
        [{"cwe": 1, "locations": [{"file": "a", "start_line": 1}], "description": "d"}] * 257
    ).encode()
    view = {"docstore/service.py": 80}
    for payload in (deep, many):
        (tmp_path / ARTIFACT).write_bytes(payload)
        cap = collect(tmp_path)
        assert cap.status == "captured"
        score = score_episode(cap.data, OK, LABELS, variant="vulnerable", agent_view=view)
        assert score.disposition.value == "invalid_output"


def test_rejected_or_absent_output_cannot_seal_as_success(tmp_path: Path) -> None:
    from aureproof.bundle import validate
    from aureproof.bundle.canonical import canonical_json
    from aureproof.bundle.run import EpisodeInput, labels_path, seal_run

    labels = LABELS.model_dump(mode="json", by_alias=True)
    ep = EpisodeInput(
        episode_id="e",
        task_id="authz-001",
        variant="vulnerable",
        labels=labels_path("authz-001"),
        agent_view={"docstore/service.py": 80},
        signals=OK,
        submission=None,
    )
    files = seal_run(
        [ep],
        {labels_path("authz-001"): canonical_json(labels)},
        [],
        cohort="t",
        generator={"name": "aureproof", "version": "test"},
    )
    assert validate(files).valid
    assert json.loads(files["verdicts.json"])[0]["disposition"] == "invalid_output"
