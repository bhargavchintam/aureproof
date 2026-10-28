# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The production Inspect runner in Docker with mockllm (issue #39; Inspect lane).

Needs the ``inspect`` extra and Docker; skipped otherwise. No provider key.
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

from aureproof.contracts import Disposition, EpisodeSpec, LabelSet
from aureproof.oracles.calibration import task_spec
from aureproof.oracles.python_spans import line_counts
from aureproof.runners.inspect_runner import InspectRunner, InspectRunnerConfig
from aureproof.runners.orchestrate import run_episode
from aureproof.runners.port import AttemptRequest
from aureproof.scoring import score_episode
from aureproof.storage import BlobStore
from aureproof.storage.ledger_store import AttemptLedgerStore

ROOT = Path(__file__).resolve().parents[2]
LABELS = LabelSet.model_validate_json(
    (ROOT / "fixtures/oracles/authz-001/labels.json").read_text("utf-8")
)
FINDINGS = [
    {
        "cwe": 862,
        "description": "delete_document has no ownership check",
        "locations": [{"file": "docstore/service.py", "symbol": "delete_document"}],
    }
]


def _docker() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


pytestmark = [pytest.mark.docker, pytest.mark.skipif(not _docker(), reason="no Docker engine")]


def _writes_findings(
    messages: list[ChatMessage], tools: list[ToolInfo], choice: ToolChoice, config: GenerateConfig
) -> ModelOutput:
    if not any(m.role == "tool" for m in messages):
        cmd = f"cat > findings.json <<'EOF'\n{json.dumps(FINDINGS)}\nEOF\necho 1 > reward.txt"
        return ModelOutput.for_tool_call("mockllm/model", "bash", {"command": cmd})
    return ModelOutput.for_tool_call("mockllm/model", "submit", {"answer": "done"})


def _refuses(
    messages: list[ChatMessage], tools: list[ToolInfo], choice: ToolChoice, config: GenerateConfig
) -> ModelOutput:
    if not any(m.role == "assistant" for m in messages):
        out = ModelOutput.from_content("mockllm/model", "I can't help with that.")
        out.choices[0].stop_reason = "content_filter"
        return out
    return ModelOutput.for_tool_call("mockllm/model", "submit", {"answer": "declined"})


def _bash_then_submit(cmd: str) -> Any:
    def policy(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        if not any(m.role == "tool" for m in messages):
            return ModelOutput.for_tool_call("mockllm/model", "bash", {"command": cmd})
        return ModelOutput.for_tool_call("mockllm/model", "submit", {"answer": "done"})

    return policy


def _run(
    tmp_path: Path, policy: Any, variant: str = "vulnerable"
) -> tuple[Any, AttemptLedgerStore]:
    cfg = InspectRunnerConfig(
        subject="reference",
        model=get_model("mockllm/model", custom_outputs=policy),
        log_dir=tmp_path / "logs",
    )
    runner = InspectRunner(cfg)
    task, system = task_spec(ROOT, "authz-001"), runner.system_spec()
    episode = EpisodeSpec.plan(
        task=task.identity,
        variant=variant,  # type: ignore[arg-type]
        system=system.identity,
        protocol="sha256:" + "3" * 64,
        repetition=0,
    )
    store = AttemptLedgerStore(tmp_path / "run")
    view = line_counts(ROOT / f"fixtures/security/authz-001/variants/{variant}")
    run = run_episode(
        store,
        BlobStore(tmp_path / "cas"),
        runner,
        AttemptRequest(episode, "", task, system, ROOT, variant),
        LABELS,
        view,
    )
    return run, store


def test_one_attempt_captures_raw_bytes_and_scores_offline(tmp_path: Path) -> None:
    run, store = _run(tmp_path, _writes_findings)
    assert run.score.disposition is Disposition.COMPLETED_WITH_FINDINGS
    assert run.score.credited == ("authz-001-d1",)  # the planted reward.txt was ignored
    assert len(run.attempts) == 1
    outcome = next(e for e in store.journal.events if e.kind == "attempt_outcome").payload or {}
    assert outcome["capture"] == "captured" and outcome["log_digest"].startswith("sha256:")
    assert outcome["provider"]["requests"] >= 2
    # Re-score from the captured bytes alone: no sandbox, same verdict.
    data = BlobStore(tmp_path / "cas").get(run.submission or "")
    view = line_counts(ROOT / "fixtures/security/authz-001/variants/vulnerable")
    again = score_episode(data, _signals(outcome), LABELS, variant="vulnerable", agent_view=view)
    assert again.credited == run.score.credited


def _signals(_: dict[str, Any]) -> Any:
    from aureproof.contracts import EpisodeSignals, RunnerOutcome

    return EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)


def test_refusal_without_findings_is_a_safety_refusal(tmp_path: Path) -> None:
    run, _ = _run(tmp_path, _refuses)
    assert run.score.disposition is Disposition.SAFETY_REFUSAL
    assert len(run.attempts) == 1  # refusals are never retried


def test_system_identity_records_pins_settings_and_tools(tmp_path: Path) -> None:
    runner = InspectRunner(
        InspectRunnerConfig(
            subject="claude_code",
            model="anthropic/claude-haiku-4-5-20251001",
            model_name="anthropic/claude-haiku-4-5-20251001",
            log_dir=tmp_path,
        )
    )
    spec = runner.system_spec()
    assert spec.settings["retry_refusals"] == 0 and spec.settings["inspect_retry_on_error"] == 0
    assert spec.models["main"].protocol == "anthropic-messages"
    assert "WebSearch" not in spec.tools and spec.subject.version == "2.1.287"


@pytest.mark.parametrize(
    ("cmd", "detail"),
    [
        ("ln -s /dev/zero findings.json", "symlink"),
        ("head -c 2000000 /dev/zero | tr '\\0' 'x' > findings.json", "oversized"),
        ("mkfifo findings.json", "not_regular_file"),
    ],
    ids=["symlink-dev-zero", "oversized-2MB", "fifo"],
)
def test_hostile_artifacts_in_the_real_sandbox(tmp_path: Path, cmd: str, detail: str) -> None:
    """Issue #40: the production collection path rejects them without unbounded reads."""
    run, store = _run(tmp_path, _bash_then_submit(cmd))
    assert run.score.disposition is Disposition.INVALID_OUTPUT
    outcome = next(e for e in store.journal.events if e.kind == "attempt_outcome").payload or {}
    assert (outcome["capture"], outcome["capture_detail"]) == ("rejected", detail)
    assert len(run.attempts) == 1  # agent output problems are never re-dispatched
