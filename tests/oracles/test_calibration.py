# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Calibration runner and `aureproof task validate` (issue #38)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aureproof.cli.main import app
from aureproof.contracts.thr import REQUIRED_CONTROLS, HealthStatus, TaskHealthRecord
from aureproof.oracles.calibration import calibrate, qualification_problems, task_spec

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "fixtures", root / "fixtures")
    return root


@pytest.mark.parametrize("task_id", ["authz-001", "path-001", "authz-002"])
def test_each_pair_is_healthy_with_every_control_and_a_reproducing_rerun(task_id: str) -> None:
    record = calibrate(ROOT, task_id)
    assert record.status is HealthStatus.HEALTHY
    assert {c.kind for c in record.controls} == REQUIRED_CONTROLS
    for control in record.controls:
        assert control.passed is True, control.kind
        assert control.input_digest.startswith("sha256:") and control.run_ids == ["calibration-1"]
    assert record.determinism.reproduced is True
    assert record.determinism.rerun_ids == ["calibration-2"]
    assert record.frozen_at is None and record.reviewed_by == []  # awaits the reviewer (#31)
    assert record.task.task_identity == task_spec(ROOT, task_id).identity
    assert record.provenance.authorship == "self-authored"
    assert qualification_problems(ROOT, task_id) == []


def test_calibration_poc_fires_on_vulnerable_only_and_ignores_irrelevant_inputs() -> None:
    record = calibrate(ROOT, "authz-001")
    poc = next(c for c in record.controls if c.kind == "calibration_poc")
    assert poc.observed == {
        "vulnerable": {"reference_positive": True, "irrelevant_trigger": False, "malformed": False},
        "repaired": {"reference_positive": False, "irrelevant_trigger": False, "malformed": False},
    }


def test_a_broken_repair_makes_the_task_unhealthy_and_validate_fail(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    variants = root / "fixtures/security/authz-001/variants"
    shutil.copy(
        variants / "vulnerable/docstore/service.py", variants / "repaired/docstore/service.py"
    )
    record = calibrate(root, "authz-001")
    assert record.status is HealthStatus.UNHEALTHY
    failed = {c.kind.value for c in record.controls if c.passed is False}
    assert {"calibration_poc", "label_lint"} <= failed
    result = runner.invoke(app, ["task", "validate", "authz-001", "--root", str(root)])
    assert result.exit_code == 1 and "UNHEALTHY" in result.output


def test_a_poc_that_cannot_run_makes_the_task_unknown(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / "fixtures/oracles/authz-001/calibration_poc.py").write_text("raise SystemExit(3)\n")
    record = calibrate(root, "authz-001")
    assert record.status is HealthStatus.UNKNOWN
    assert "calibration_poc" in record.status_reason
    assert runner.invoke(app, ["task", "validate", "authz-001", "--root", str(root)]).exit_code == 1


def test_a_leaked_oracle_canary_fails_qualification(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    oracle = json.loads((root / "fixtures/dataset.json").read_text())["tasks"][0]["oracle_canary"]
    agent_file = root / "fixtures/security/authz-001/instruction.md"
    agent_file.write_text(agent_file.read_text() + f"\n<!-- {oracle} -->\n")
    assert any("leaked" in p for p in qualification_problems(root, "authz-001"))
    assert runner.invoke(app, ["task", "validate", "authz-001", "--root", str(root)]).exit_code == 1


def test_task_validate_cli(tmp_path: Path) -> None:
    out = tmp_path / "thr.json"
    result = runner.invoke(
        app, ["task", "validate", "authz-001", "--root", str(ROOT), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert "HEALTHY" in result.output and "unreviewed" in result.output
    TaskHealthRecord.model_validate_json(out.read_text("utf-8"))
    assert runner.invoke(app, ["task", "validate", "nope", "--root", str(ROOT)]).exit_code == 2


@pytest.mark.parametrize("unregistered", ["authz-999"])
def test_unregistered_task_is_a_qualification_problem(unregistered: str) -> None:
    assert qualification_problems(ROOT, unregistered) == [
        f"{unregistered} is not registered in fixtures/dataset.json"
    ]
