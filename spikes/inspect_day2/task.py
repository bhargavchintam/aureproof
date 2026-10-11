# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Day-2 Inspect spike task for fixture pair authz-001 (issue #7, AP-034).

    uv run --extra inspect inspect eval spikes/inspect_day2/task.py \
        -T subject=scripted --model mockllm/model

Subjects: ``scripted`` (react + mockllm policy), ``bridge_probe`` (bridge
plumbing, egress, and key-isolation probe), ``claude_code`` (inspect_swe).
"""

from __future__ import annotations

import sys
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import as_solver, react
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_ai.solver import Solver
from inspect_ai.tool import bash

sys.path.insert(0, str(Path(__file__).parent))

from agents import bridge_probe, fail_first_attempt, scripted_policy
from scorer import collect_findings, findings_matcher

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
TASK_ID = "authz-001"
AGENT_VIEW = ROOT / "fixtures" / "security" / TASK_ID
CLAUDE_CODE_VERSION = "2.1.287"  # exact pin; pre-cache with download_agent_binary


def _sample(variant: str) -> Sample:
    """Only the variant's ``docstore/`` reaches the sandbox, at /work/docstore."""
    pkg = AGENT_VIEW / "variants" / variant / "docstore"
    files = {f"docstore/{p.name}": str(p) for p in sorted(pkg.glob("*.py"))}
    return Sample(
        id=f"{TASK_ID}:{variant}",
        input=(AGENT_VIEW / "instruction.md").read_text(),
        files=files,
        metadata={"task_id": TASK_ID, "variant": variant, "cluster_id": TASK_ID},
    )


def _subject(name: str) -> Solver:
    if name == "scripted":
        model = get_model("mockllm/model", custom_outputs=scripted_policy)
        return as_solver(react(tools=[bash(timeout=60)], model=model))
    if name == "bridge_probe":
        return as_solver(bridge_probe())
    if name == "claude_code":
        from inspect_swe import claude_code

        return as_solver(
            claude_code(
                version=CLAUDE_CODE_VERSION,
                cwd="/work",
                disallowed_tools=["WebSearch", "WebFetch"],
                retry_refusals=0,  # a refusal is its own outcome, never retried away
                retry_uncaught_errors=0,  # Aureproof owns attempts (ADR-0003)
            )
        )
    raise ValueError(f"unknown subject: {name}")


@task
def authz_spike(
    subject: str = "scripted",
    fail_first: bool = False,
    token_limit: int | None = None,
    time_limit: int | None = None,
) -> Task:
    """Per-sample budgets (tokens, wall-clock seconds) bound live-model cost."""
    solvers = [fail_first_attempt()] if fail_first else []
    return Task(
        dataset=[_sample("vulnerable"), _sample("repaired")],
        solver=[*solvers, _subject(subject), collect_findings()],
        scorer=findings_matcher(),
        sandbox=("docker", str(HERE / "compose.yaml")),
        token_limit=token_limit,
        time_limit=time_limit,
    )
