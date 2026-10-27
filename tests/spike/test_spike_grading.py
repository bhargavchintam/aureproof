# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Spike grading, key handling and leak scanning without Inspect or Docker (issue #34).

These run in ordinary CI. The Docker + mockllm lane
(tests/integration/test_inspect_spike.py, .github/workflows/inspect-lane.yml)
exercises capture, re-score and bridge readiness separately.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

from aureproof.contracts import EpisodeSignals, RunnerOutcome

SPIKE = Path(__file__).resolve().parents[2] / "spikes" / "inspect_day2"
sys.path.insert(0, str(SPIKE))

from grading import agent_view, grade, verdict_summary  # noqa: E402
from keys import KeyFileError, leak_hits, load_key  # noqa: E402

TASK = "authz-001"


def capture(findings: Any) -> dict[str, Any]:
    text = json.dumps(findings)
    return {"status": "captured", "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}


def finding(cwe: int, symbol: str, file: str = "docstore/service.py") -> dict[str, Any]:
    return {"cwe": cwe, "locations": [{"file": file, "symbol": symbol}], "description": "d"}


def test_agent_view_is_the_mounted_workspace() -> None:
    view = agent_view(TASK, "vulnerable")
    assert set(view) == {
        f"docstore/{m}.py" for m in ("__init__", "api", "auth", "models", "service")
    }
    assert all(n > 0 for n in view.values())


@pytest.mark.parametrize(
    ("variant", "findings", "verdicts", "disposition"),
    [
        ("vulnerable", [finding(862, "delete_document")], ["confirmed"], "completed_with_findings"),
        ("repaired", [finding(862, "delete_document")], ["refuted"], "completed_with_findings"),
        (
            "repaired",
            [finding(862, "handle_request", "docstore/api.py")],
            ["refuted"],
            "completed_with_findings",
        ),
        (
            "vulnerable",
            [finding(862, "delete_document"), finding(639, "delete_document")],
            ["confirmed", "duplicate"],
            "completed_with_findings",
        ),
        (
            "vulnerable",
            [finding(89, "delete_document")],
            ["unresolved:class_mismatch"],
            "completed_with_findings",
        ),
        ("vulnerable", [], [], "completed_no_findings"),
    ],
)
def test_current_labels_grade_through_the_core(
    variant: str, findings: list[Any], verdicts: list[str], disposition: str
) -> None:
    graded = grade(capture(findings), task_id=TASK, variant=variant)
    assert verdict_summary(graded) == verdicts
    assert graded["disposition"] == disposition
    assert graded["findings_sha256"] == capture(findings)["sha256"]


def test_missing_submission_refusal_and_missing_evidence() -> None:
    absent = {"status": "no_submission"}
    assert grade(absent, task_id=TASK, variant="vulnerable")["disposition"] == "invalid_output"
    refusal = EpisodeSignals(
        evidence_complete=True, runner_outcome=RunnerOutcome.OK, refusal_signal=True
    )
    assert grade(absent, task_id=TASK, variant="vulnerable", signals=refusal)["disposition"] == (
        "safety_refusal"
    )
    incomplete = EpisodeSignals(evidence_complete=False, runner_outcome=RunnerOutcome.OK)
    graded = grade(
        capture([finding(862, "delete_document")]),
        task_id=TASK,
        variant="vulnerable",
        signals=incomplete,
    )
    assert graded["disposition"] == "evidence_incomplete" and graded["verdicts"] == []


def test_leak_scan_finds_a_planted_secret(tmp_path: Path) -> None:
    log = tmp_path / "fake.eval"
    with zipfile.ZipFile(log, "w") as archive:
        archive.writestr("samples/1.json", '{"env": "sk-ant-canary-123"}')
        archive.writestr("header.json", "{}")
    assert leak_hits(log, "sk-ant-canary-123") == ["samples/1.json"]
    assert leak_hits(log, "sk-ant-other") == []


def test_key_file_must_be_private(tmp_path: Path) -> None:
    env_file = tmp_path / "spike.env"
    with pytest.raises(KeyFileError, match="missing"):
        load_key(env_file)
    env_file.write_text("export ANTHROPIC_API_KEY='sk-ant-test'\n")
    env_file.chmod(0o644)
    with pytest.raises(KeyFileError, match="chmod 600"):
        load_key(env_file)
    env_file.chmod(0o600)
    assert load_key(env_file) == "sk-ant-test"
    env_file.write_text("OTHER=1\n")
    with pytest.raises(KeyFileError, match="not found"):
        load_key(env_file)
