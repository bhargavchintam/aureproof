# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The reference subject's pinned prompt and tool-call extraction (issue #43)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from aureproof.runners import reference
from aureproof.runners.inspect_runner import tool_calls


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_prompt_is_pinned_and_free_of_grading_hints() -> None:
    assert reference.reference_prompt_digest() == _sha(reference.REFERENCE_PROMPT)
    lowered = reference.REFERENCE_PROMPT.lower()
    for leak in ("label", "cwe-862", "delete_document", "score", "reward", "canary"):
        assert leak not in lowered


def test_reference_tool_events_are_controller_observed() -> None:
    sample = NS(
        events=[
            NS(event="model", output=None),
            NS(
                event="tool",
                function="bash",
                arguments={"command": "ls"},
                result="service.py\n",
                error=None,
            ),
            NS(
                event="tool",
                function="bash",
                arguments={"command": "sleep 99"},
                result="",
                error=NS(type="timeout"),
            ),
        ]
    )
    calls, source = tool_calls(sample, "reference")
    assert source == "controller_observed"
    assert [(c.tool, c.error) for c in calls] == [("bash", None), ("bash", "timeout")]
    assert calls[0].input_sha256 == _sha(json.dumps({"command": "ls"}, separators=(",", ":")))
    assert calls[0].output_sha256 == _sha("service.py\n")


def test_claude_code_tool_calls_are_agent_reported_without_outputs() -> None:
    message = NS(tool_calls=[NS(function="Read", arguments={"file_path": "/work/a.py"})])
    sample = NS(
        events=[
            NS(event="model", output=NS(choices=[NS(message=message)])),
            NS(event="model", output=NS(choices=[])),
            NS(event="tool", function="ignored", arguments={}, result="", error=None),
        ]
    )
    calls, source = tool_calls(sample, "claude_code")
    assert source == "agent_reported"
    assert [(c.tool, c.output_sha256) for c in calls] == [("Read", None)]


def test_the_prompt_is_part_of_the_system_identity(tmp_path: Path) -> None:
    pytest.importorskip("inspect_ai")
    from aureproof.runners.inspect_runner import InspectRunnerConfig, system_spec

    cfg = InspectRunnerConfig(subject="reference", model="mockllm/model", log_dir=tmp_path)
    spec = system_spec(cfg)
    assert spec.prompts == {"system": reference.reference_prompt_digest()}
    assert spec.settings["retry_refusals"] == 0 and spec.settings["attempts"] == 1
    changed = spec.model_copy(update={"prompts": {"system": _sha("another prompt")}})
    assert changed.identity != spec.identity
    other = system_spec(dataclasses.replace(cfg, subject="claude_code"))
    assert other.prompts == {}  # Claude Code's own prompt is pinned by its version
