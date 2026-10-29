# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Per-sample facts read from an Inspect log sample (issue #39)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from aureproof.runners.inspect_runner import (
    CLAUDE_CODE_LIVE_ONLY_TOOLS,
    CLAUDE_CODE_TOOLS,
    facts_from_sample,
)


def _model_event(*request_ids: object) -> SimpleNamespace:
    return SimpleNamespace(
        event="model",
        tools=[],
        output=SimpleNamespace(stop_reason="end_turn", choices=[]),
        request_ids=list(request_ids),
        retries=0,
    )


def test_provider_request_ids_are_recorded_as_strings(tmp_path: Path) -> None:
    """Inspect 0.3.283 reports ModelRequestId(id, header, status), not a string.

    Found by the first live slice (#47): a mock model reports no request IDs, so
    only a real provider call reached the ledger's string check and failed it.
    """
    log = tmp_path / "run.eval"
    log.write_bytes(b"log")
    live = SimpleNamespace(id="req_011live", header="request-id", status=200)
    sample = SimpleNamespace(
        events=[_model_event(live), _model_event("req_plain")],
        store={},
        error=None,
        limit=None,
        error_retries=[],
    )
    facts = facts_from_sample(sample, log, "run-1")
    assert list(facts.request_ids) == ["req_011live", "req_plain"]


# The 22 tools Claude Code 2.1.287 offered on Haiku 4.5 in every episode of the first
# live slice (2026-10-29, logs read with inspect_ai.log.read_eval_log).
LIVE_SURFACE = frozenset(
    {
        "Agent", "Bash", "CronCreate", "CronDelete", "CronList", "Edit", "EnterWorktree",
        "ExitWorktree", "ListAgents", "NotebookEdit", "Read", "ReportFindings",
        "ScheduleWakeup", "SendMessage", "Skill", "TaskCreate", "TaskGet", "TaskList",
        "TaskStop", "TaskUpdate", "Workflow", "Write",
    }
)  # fmt: skip


def test_the_declared_claude_code_surface_covers_the_live_one() -> None:
    """The first live slice stopped every episode as tool_surface_mismatch.

    The task-list tools are offered with a real model but were not offered to the
    scripted model the declaration was first taken from.
    """
    assert frozenset(CLAUDE_CODE_TOOLS) == LIVE_SURFACE
    assert "WebSearch" not in CLAUDE_CODE_TOOLS and "WebFetch" not in CLAUDE_CODE_TOOLS
    assert set(CLAUDE_CODE_LIVE_ONLY_TOOLS) <= set(CLAUDE_CODE_TOOLS)
