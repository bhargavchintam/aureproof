# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Bridge preflight: unsupported capabilities fail before dispatch (issue #42)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from aureproof.runners.inspect_runner import (
    InspectRunner,
    InspectRunnerConfig,
    UnsupportedCapability,
    preflight,
    system_spec,
)

CC = InspectRunnerConfig(subject="claude_code", model="mockllm/model", log_dir=Path("logs"))
REF = dataclasses.replace(CC, subject="reference")


def test_claude_code_discloses_the_bridge_translation_in_its_identity() -> None:
    pytest.importorskip("inspect_ai")  # system_spec records Inspect's version
    transformations = preflight(CC)
    assert any("sandbox_agent_bridge" in t for t in transformations)
    assert system_spec(CC).settings["transformations"] == transformations
    assert preflight(REF) == []


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (dataclasses.replace(CC, hosted_tools="web-search"), "web-search is not implemented"),
        (dataclasses.replace(REF, hosted_tools="web-search"), "no hosted tools"),
        (
            dataclasses.replace(CC, model="openai/gpt-x", model_name="openai/gpt-x"),
            "needs an Anthropic Messages provider",
        ),
        (dataclasses.replace(CC, model="anthropic/claude-x"), "differs from the recorded"),
    ],
    ids=["cc-web-search", "reference-web-search", "cc-other-provider", "identity-mismatch"],
)
def test_unsupported_capabilities_fail_before_any_dispatch(
    config: InspectRunnerConfig, message: str
) -> None:
    with pytest.raises(UnsupportedCapability, match=message):
        preflight(config)
    with pytest.raises(UnsupportedCapability):
        InspectRunner(config)  # never reaches run_attempt, so never re-dispatched
    with pytest.raises(UnsupportedCapability):
        system_spec(config)  # no identity is minted for an unqualified system


def test_qualified_configurations_pass_preflight() -> None:
    assert preflight(REF) == []
    assert len(preflight(CC)) == 2


def test_anthropic_claude_code_is_qualified() -> None:
    pytest.importorskip("inspect_ai")
    config = dataclasses.replace(CC, model="anthropic/claude-x", model_name="anthropic/claude-x")
    assert InspectRunner(config).system_spec().models["main"].protocol == "anthropic-messages"
