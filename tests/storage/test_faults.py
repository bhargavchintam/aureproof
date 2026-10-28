# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Fault injection on bundle and blob writes (issue #55): partial writes never pass."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from aureproof.bundle import validate
from aureproof.storage import BlobStore, StorageError, read_bundle, write_bundle

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL = ROOT / "examples" / "bundles" / "tutorial-v0.1"


def test_a_crash_while_writing_a_bundle_leaves_nothing_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = read_bundle(TUTORIAL)
    calls = {"n": 0}
    real_fsync = os.fsync

    def crash_on_the_fourth_file(fd: int) -> None:
        calls["n"] += 1
        if calls["n"] == 4:
            raise OSError("disk went away")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", crash_on_the_fourth_file)
    target = tmp_path / "bundle"
    with pytest.raises(OSError, match="disk went away"):
        write_bundle(files, target)
    assert not target.exists()  # no half-written bundle under the real name
    assert list(tmp_path.iterdir()) == []  # and no temporary directory left over


@pytest.mark.parametrize("damage", ["missing-member", "truncated-member", "truncated-journal"])
def test_a_partially_written_bundle_never_validates(tmp_path: Path, damage: str) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(TUTORIAL, bundle)
    if damage == "missing-member":
        (bundle / "metrics.json").unlink()
    elif damage == "truncated-member":
        data = (bundle / "verdicts.json").read_bytes()
        (bundle / "verdicts.json").write_bytes(data[: len(data) // 2])
    else:
        data = (bundle / "journal.jsonl").read_bytes()
        (bundle / "journal.jsonl").write_bytes(data[: len(data) - 7])
    report = validate(read_bundle(bundle))
    assert not report.valid, damage
    assert report.problems()


def test_a_torn_blob_from_an_earlier_crash_is_detected_and_never_reused(tmp_path: Path) -> None:
    store = BlobStore(tmp_path / "cas")
    data = b'[{"cwe": 862}]'
    ref = store.put(data)
    path = tmp_path / "cas" / "sha256" / ref.removeprefix("sha256:")
    path.write_bytes(data[:5])  # a crash left half the bytes under the final name
    with pytest.raises(StorageError, match="does not match its content"):
        store.get(ref)
    with pytest.raises(StorageError):
        store.put(data)  # the torn copy is not silently accepted as the blob
