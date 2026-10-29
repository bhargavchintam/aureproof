# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The Claude Code binary is pinned by checksum and checked before dispatch (issue #48)."""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

import pytest

from aureproof.runners.inspect_runner import (
    CLAUDE_CODE_CHECKSUMS,
    InspectRunner,
    InspectRunnerConfig,
    UnsupportedCapability,
    preflight,
    system_spec,
    verify_cached_binaries,
)

CC = InspectRunnerConfig(subject="claude_code", model="mockllm/model", log_dir=Path("logs"))


def test_the_pinned_version_has_a_checksum_for_every_linux_sandbox_platform() -> None:
    pins = CLAUDE_CODE_CHECKSUMS[CC.claude_code_version]
    assert set(pins) == {"linux-arm64", "linux-x64", "linux-arm64-musl", "linux-x64-musl"}
    assert all(len(v) == 64 and int(v, 16) >= 0 for v in pins.values())


def test_an_unpinned_version_fails_preflight() -> None:
    with pytest.raises(UnsupportedCapability, match="no pinned checksums"):
        preflight(dataclasses.replace(CC, claude_code_version="9.9.9"))


def test_the_checksums_enter_the_system_identity() -> None:
    pytest.importorskip("inspect_ai")  # system_spec records Inspect's version
    pins = system_spec(CC).settings["binary_sha256"]
    assert pins == CLAUDE_CODE_CHECKSUMS[CC.claude_code_version]


def test_cached_binaries_must_match_their_pins(tmp_path: Path) -> None:
    good = b"the real binary"
    pins = {"9.0.0": {"linux-arm64": hashlib.sha256(good).hexdigest(), "linux-x64": "0" * 64}}
    (tmp_path / "claude-9.0.0-linux-arm64").write_bytes(good)
    (tmp_path / "claude-8.0.0-linux-x64").write_bytes(b"another version, not checked")
    assert verify_cached_binaries(tmp_path, "9.0.0", pins) == []

    (tmp_path / "claude-9.0.0-linux-x64").write_bytes(b"tampered")
    assert verify_cached_binaries(tmp_path, "9.0.0", pins) == [
        "claude-9.0.0-linux-x64: sha256 differs from the pinned checksum"
    ]
    (tmp_path / "claude-9.0.0-linux-riscv").write_bytes(b"?")
    assert "claude-9.0.0-linux-riscv: no pinned checksum for this platform" in (
        verify_cached_binaries(tmp_path, "9.0.0", pins)
    )


def test_the_runner_refuses_a_tampered_cached_binary(tmp_path: Path) -> None:
    (tmp_path / f"claude-{CC.claude_code_version}-linux-arm64").write_bytes(b"tampered")
    with pytest.raises(UnsupportedCapability, match="differs from the pinned checksum"):
        InspectRunner(dataclasses.replace(CC, binary_cache=tmp_path))
    InspectRunner(dataclasses.replace(CC, binary_cache=tmp_path / "empty"))  # nothing cached yet
