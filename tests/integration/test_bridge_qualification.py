# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Bridge capability qualification on the production Claude Code path (issue #42).

Claude Code (inspect_swe) runs in the Docker sandbox behind Inspect's
``sandbox_agent_bridge``; a scripted ``mockllm`` model drives it, so no provider
key is needed. Each test checks one declared control from the outside: what the
sandbox could see or reach, what the agent was offered, and what the controller
journaled. Needs the ``inspect`` extra and Docker; skipped otherwise.
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("inspect_ai")
pytest.importorskip("inspect_swe")

from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, ModelUsage, get_model
from inspect_ai.tool import ToolChoice, ToolInfo

from aureproof.contracts import Budget, Disposition, EpisodeSpec, LabelSet
from aureproof.contracts.dataset import DatasetRegistry
from aureproof.oracles.calibration import task_spec
from aureproof.oracles.python_spans import line_counts
from aureproof.runners.inspect_runner import (
    CLAUDE_CODE_LIVE_ONLY_TOOLS,
    CLAUDE_CODE_TOOLS,
    InspectRunner,
    InspectRunnerConfig,
)
from aureproof.runners.orchestrate import EpisodeRun, run_episode
from aureproof.runners.port import AttemptRequest
from aureproof.storage import BlobStore
from aureproof.storage.ledger_store import AttemptLedgerStore

ROOT = Path(__file__).resolve().parents[2]
TASK = "authz-001"
LABELS = LabelSet.model_validate_json(
    (ROOT / f"fixtures/oracles/{TASK}/labels.json").read_text("utf-8")
)
ORACLE_CANARY = next(
    t.oracle_canary
    for t in DatasetRegistry.model_validate_json(
        (ROOT / "fixtures/dataset.json").read_text("utf-8")
    ).tasks
    if t.task_id == TASK
)
EGRESS = (
    'python3 -c "import socket\n'
    "for host in [('1.1.1.1', 443), ('example.com', 80)]:\n"
    "    try:\n"
    "        socket.create_connection(host, timeout=3); print('EGRESS-OPEN', host)\n"
    "    except OSError as e:\n"
    "        print('EGRESS-BLOCKED', host, type(e).__name__)\""
)


def _docker() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


pytestmark = [pytest.mark.docker, pytest.mark.skipif(not _docker(), reason="no Docker engine")]


class Script:
    """A mock model that runs Claude Code tools in order, then stops.

    Records every request it served and the text of every tool result it saw,
    so a test can check what the sandbox returned.
    """

    def __init__(self, *calls: tuple[str, dict[str, Any]], usage: int | None = None) -> None:
        self.calls = list(calls)
        self.requests = 0
        self.tool_results: list[str] = []
        self.offered: list[str] = []
        self.usage = usage

    def __call__(
        self,
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        self.requests += 1
        self.offered = sorted(t.name for t in tools)
        self.tool_results = [m.text for m in messages if m.role == "tool"]
        step = len([m for m in messages if m.role == "assistant"])
        if step < len(self.calls):
            name, args = self.calls[step]
            out = ModelOutput.for_tool_call("mockllm/model", name, args)
        else:
            out = ModelOutput.from_content("mockllm/model", "Review finished.")
        if self.usage is not None:
            out.usage = ModelUsage(
                input_tokens=self.usage, output_tokens=1000, total_tokens=self.usage + 1000
            )
        return out


def _run(
    tmp_path: Path, script: Script, budget: Budget | None = None
) -> tuple[EpisodeRun, AttemptLedgerStore]:
    cfg = InspectRunnerConfig(
        subject="claude_code",
        model=get_model("mockllm/model", custom_outputs=script),
        log_dir=tmp_path / "logs",
        budget=budget or Budget(),
    )
    runner = InspectRunner(cfg)
    task, system = task_spec(ROOT, TASK), runner.system_spec()
    episode = EpisodeSpec.plan(
        task=task.identity,
        variant="vulnerable",
        system=system.identity,
        protocol="sha256:" + "4" * 64,
        repetition=0,
    )
    store = AttemptLedgerStore(tmp_path / "run")
    run = run_episode(
        store,
        BlobStore(tmp_path / "cas"),
        runner,
        AttemptRequest(episode, "", task, system, ROOT, "vulnerable"),
        LABELS,
        line_counts(ROOT / f"fixtures/security/{TASK}/variants/vulnerable"),
    )
    return run, store


def _log_bytes(tmp_path: Path) -> bytes:
    [log] = (tmp_path / "logs").glob("*.eval")
    with zipfile.ZipFile(log) as z:
        return b"".join(z.read(name) for name in z.namelist())


def test_no_provider_key_or_evaluator_label_reaches_the_sandbox_or_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-INFO-1, T-INFO-2: a planted host key and the labels stay outside."""
    sentinel = f"sk-ant-sentinel-{uuid.uuid4().hex}"
    monkeypatch.setenv("ANTHROPIC_API_KEY", sentinel)
    script = Script(
        ("Bash", {"command": "env", "description": "list the environment"}),
        ("Bash", {"command": "ls -la /work; ls -R / 2>/dev/null | grep -c labels.json"}),
    )
    run, _ = _run(tmp_path, script)
    env_output, listing = script.tool_results[:2]
    env = dict(line.split("=", 1) for line in env_output.splitlines() if "=" in line)
    assert "PATH" in env  # the command really ran in the sandbox
    assert sentinel not in env_output and "ANTHROPIC_API_KEY" not in env
    base_url = env["ANTHROPIC_BASE_URL"]  # Claude Code talks only to the in-sandbox bridge
    assert "localhost" in base_url or "127.0.0.1" in base_url, base_url
    assert "docstore" in listing and "labels.json" not in listing.splitlines()[0:-1]
    assert listing.strip().splitlines()[-1] == "0"  # no labels file anywhere in the sandbox
    log = _log_bytes(tmp_path)
    assert sentinel.encode() not in log
    assert ORACLE_CANARY.encode() not in log
    for defect in LABELS.defects:
        assert defect.defect_id.encode() not in log
    assert run.score.disposition is Disposition.INVALID_OUTPUT  # nothing was submitted


def test_sandbox_outbound_traffic_fails(tmp_path: Path) -> None:
    """T-ELEV-1: no route out of the sandbox, by address or by name."""
    script = Script(("Bash", {"command": EGRESS, "description": "probe the network"}))
    _run(tmp_path, script)
    [output] = script.tool_results
    assert output.count("EGRESS-BLOCKED") == 2, output
    assert "EGRESS-OPEN" not in output


def test_hosted_tools_are_withheld_and_a_call_to_one_is_rejected(tmp_path: Path) -> None:
    """T-ELEV-2: closed-world offers no WebSearch or WebFetch, and calling one fails."""
    script = Script(("WebFetch", {"url": "https://example.com", "prompt": "summarize"}))
    _, store = _run(tmp_path, script)
    assert script.offered == sorted(set(CLAUDE_CODE_TOOLS) - set(CLAUDE_CODE_LIVE_ONLY_TOOLS))
    assert "WebSearch" not in script.offered and "WebFetch" not in script.offered
    [result] = script.tool_results
    assert "No such tool available: WebFetch" in result, result
    outcome = [e for e in store.journal.events if e.kind == "attempt_outcome"]
    assert (outcome[-1].payload or {}).get("error_class") is None  # the agent ran on


def test_token_budget_ends_the_episode_without_extra_opportunities(tmp_path: Path) -> None:
    """T-DOS-4: the budget becomes budget_exhausted, in one attempt."""
    script = Script(*[("Bash", {"command": "ls"})] * 20, usage=4000)
    run, _ = _run(tmp_path, script, Budget(max_tokens=8000))
    assert run.score.disposition is Disposition.BUDGET_EXHAUSTED
    assert len(run.attempts) == 1
    assert script.requests <= 3  # stopped once the limit was crossed


def test_time_budget_ends_the_episode_without_extra_opportunities(tmp_path: Path) -> None:
    """T-DOS-4: wall-clock time is enforced on the agent's own tool use."""
    script = Script(("Bash", {"command": "sleep 30", "timeout": 60000}))
    run, store = _run(tmp_path, script, Budget(max_seconds=8))
    assert run.score.disposition is Disposition.BUDGET_EXHAUSTED
    assert len(run.attempts) == 1
    [outcome] = [e for e in store.journal.events if e.kind == "attempt_outcome"]
    assert (outcome.payload or {})["error_class"] == "limit:time"


def test_model_calls_are_journaled_by_the_controller_with_their_trust_tier(
    tmp_path: Path,
) -> None:
    """Every streamed model call is observed at the bridge and journaled; tool calls
    that only Claude Code executed are agent_reported."""
    script = Script(("Bash", {"command": "echo '[]' > findings.json"}))
    run, store = _run(tmp_path, script)
    assert run.score.disposition is Disposition.COMPLETED_NO_FINDINGS
    [outcome] = [e for e in store.journal.events if e.kind == "attempt_outcome"]
    assert outcome.observation_source == "controller_observed"
    provider = (outcome.payload or {})["provider"]
    assert provider["requests"] == script.requests and provider["retries"] == 0
    tools = [e for e in store.journal.events if e.kind == "tool_observed"]
    assert [(e.payload or {})["tool"] for e in tools] == ["Bash"]
    assert {e.observation_source for e in tools} == {"agent_reported"}
