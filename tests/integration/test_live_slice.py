# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The M2 evidence chain on the real Inspect path, with mockllm (issue #47; Inspect lane).

Protocol, system and task identities, the attempt journal with model and tool
observations, the captured submissions and the controller's verdicts are sealed
into one bundle on disk; the CLI then validates and re-scores it offline, as a
third party would. Only the live model and the signature are missing (#7, #47).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("inspect_ai")

from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo
from typer.testing import CliRunner

from aureproof.cli.main import app
from aureproof.contracts.decision import CohortTask, Configurations, DecisionProtocol
from aureproof.oracles.calibration import calibrate, task_spec
from aureproof.runners.inspect_runner import InspectRunner, InspectRunnerConfig
from aureproof.runners.slice import run_slice, thr_digest
from aureproof.storage import write_bundle

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = [
    {
        "cwe": 862,
        "description": "delete_document has no ownership check",
        "locations": [{"file": "docstore/service.py", "symbol": "delete_document"}],
    }
]
cli = CliRunner()


def _docker() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


pytestmark = [pytest.mark.docker, pytest.mark.skipif(not _docker(), reason="no Docker engine")]


def _reviewer(
    messages: list[ChatMessage], tools: list[ToolInfo], choice: ToolChoice, config: GenerateConfig
) -> ModelOutput:
    if not any(m.role == "tool" for m in messages):
        cmd = f"cat > findings.json <<'EOF'\n{json.dumps(FINDINGS)}\nEOF"
        return ModelOutput.for_tool_call("mockllm/model", "bash", {"command": cmd})
    return ModelOutput.for_tool_call("mockllm/model", "submit", {"answer": "done"})


def test_the_chain_is_sealed_and_a_third_party_rescores_it_offline(tmp_path: Path) -> None:
    runner = InspectRunner(
        InspectRunnerConfig(
            subject="reference",
            model=get_model("mockllm/model", custom_outputs=_reviewer),
            log_dir=tmp_path / "logs",
        )
    )
    system = runner.system_spec()
    thr = calibrate(ROOT, "authz-001")
    protocol = DecisionProtocol(
        protocol_version="0.1",
        name="m2-slice-lane",
        cohort=[
            CohortTask(
                task_identity=task_spec(ROOT, "authz-001").identity,
                thr_digest=thr_digest(thr),
                cluster_id="authz-001",
            )
        ],
        configurations=Configurations(A=system.identity, B="sha256:" + "9" * 64),
        repetitions=1,
        margin=0.05,
    )
    files = run_slice(ROOT, protocol, [thr], runner, work=tmp_path / "work")
    bundle = tmp_path / "bundle"
    write_bundle(files, bundle)

    validated = cli.invoke(app, ["validate", str(bundle)])
    assert validated.exit_code == 0, validated.output
    scored = cli.invoke(app, ["score", str(bundle), "--offline"])
    assert scored.exit_code == 0 and "re-score: reproduced" in scored.output, scored.output

    events: list[dict[str, Any]] = [
        json.loads(line)["event"] for line in files["journal.jsonl"].splitlines()
    ]
    tools = [e for e in events if e["kind"] == "tool_observed"]
    assert {e["observation_source"] for e in tools} == {"controller_observed"}
    outcomes = [e for e in events if e["kind"] == "attempt_outcome"]
    assert len(outcomes) == 2 and all(e["blob_refs"] for e in outcomes)
    verdicts = {v["episode_id"]: v for v in json.loads(files["verdicts.json"])}
    by_variant = {e["variant"]: e for e in json.loads(files["episodes.json"])}
    vulnerable = verdicts[by_variant["vulnerable"]["episode_id"]]
    repaired = verdicts[by_variant["repaired"]["episode_id"]]
    assert [v["verdict"] for v in vulnerable["verdicts"]] == ["confirmed"]
    assert [v["verdict"] for v in repaired["verdicts"]] == ["refuted"]


def test_run_cli_refuses_a_protocol_that_names_another_system(tmp_path: Path) -> None:
    thr = calibrate(ROOT, "authz-001")
    (tmp_path / "thr.json").write_text(thr.model_dump_json(), encoding="utf-8")
    protocol = DecisionProtocol(
        protocol_version="0.1",
        name="other-systems",
        cohort=[
            CohortTask(
                task_identity=task_spec(ROOT, "authz-001").identity,
                thr_digest=thr_digest(thr),
                cluster_id="authz-001",
            )
        ],
        configurations=Configurations(A="sha256:" + "7" * 64, B="sha256:" + "8" * 64),
        repetitions=1,
        margin=0.05,
    )
    (tmp_path / "protocol.json").write_text(protocol.model_dump_json(), encoding="utf-8")
    args = [
        "run",
        "--protocol",
        str(tmp_path / "protocol.json"),
        "--thr",
        str(tmp_path / "thr.json"),
        "--model",
        "mockllm/model",
        "--out",
        str(tmp_path / "bundle"),
        "--log-dir",
        str(tmp_path / "logs"),
        "--root",
        str(ROOT),
    ]
    result = cli.invoke(app, args)
    assert result.exit_code == 2, result.output
    assert "neither configuration A nor B" in result.output
    assert not (tmp_path / "bundle").exists() and not (tmp_path / "logs").exists()
