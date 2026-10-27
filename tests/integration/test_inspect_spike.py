# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Regression test for the Day-2 Inspect spike (issue #7, AP-034).

Runs the scripted ``mockllm`` subject on authz-001 inside a Docker sandbox with
``network_mode: none`` and checks the evidence the spike relies on. Needs the
``inspect`` extra and a Docker engine; skipped otherwise (as in CI today):

    uv run --extra inspect pytest tests/integration/test_inspect_spike.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("inspect_ai")
pytest.importorskip("inspect_swe")

ROOT = Path(__file__).resolve().parents[2]
SPIKE = ROOT / "spikes" / "inspect_day2"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not _docker_available(), reason="Docker engine not available"),
]


@pytest.fixture(scope="module")
def spike_modules() -> None:
    sys.path.insert(0, str(SPIKE))


def _run(tmp_path: Path, subject: str) -> str:
    from inspect_ai import eval as inspect_eval
    from task import authz_spike

    [log] = inspect_eval(
        authz_spike(subject=subject),
        model="mockllm/model",
        log_dir=str(tmp_path),
        display="none",
    )
    assert log.status == "success"
    assert log.location is not None
    return log.location


def test_scripted_subject_grades_from_captured_findings_only(
    tmp_path: Path, spike_modules: None
) -> None:
    from inspect_ai.log import read_eval_log

    log = read_eval_log(_run(tmp_path, "scripted"))
    by_id = {str(s.id): s for s in log.samples or []}
    expected = {"authz-001:vulnerable": ["confirmed"], "authz-001:repaired": ["refuted"]}
    for sample_id, verdicts in expected.items():
        sample = by_id[sample_id]
        assert sample.error is None
        score = (sample.scores or {})["findings_matcher"]
        assert [v["verdict"] for v in (score.metadata or {})["verdicts"]] == verdicts
        # The agent planted verdict.json and reward.txt claiming success; the
        # repaired sample is still refuted, so the forgeries were not read.
        workspace = next(m.text for m in sample.messages if m.role == "tool")
        assert "verdict.json" in workspace and "reward.txt" in workspace


def test_offline_rescore_reproduces_live_verdicts(tmp_path: Path, spike_modules: None) -> None:
    from rescore import rescore

    live, again = rescore(_run(tmp_path, "scripted"))
    assert live and live == again


def test_bridge_works_without_network_and_without_provider_env(
    tmp_path: Path, spike_modules: None
) -> None:
    from inspect_ai.log import read_eval_log

    for sample in read_eval_log(_run(tmp_path, "bridge_probe")).samples or []:
        report = sample.store["probe_report"]
        assert report["proxy"]["ok"], report
        assert report["egress"].startswith("blocked"), report["egress"]
        assert not [n for n in report["env_names"] if n.startswith(("ANTHROPIC", "OPENAI"))]
        assert any(e.event == "model" for e in sample.events)  # controller-observed call
