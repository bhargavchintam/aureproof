# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Canaries, splits and exposure from the public dataset registry (issue #45).

Driven by fixtures/dataset.json, not by private labels: the check works the
same in the private assessment repository, and prints only file paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aureproof.contracts.dataset import DatasetRegistry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = DatasetRegistry.model_validate_json((ROOT / "fixtures/dataset.json").read_text("utf-8"))
SECURITY = ROOT / "fixtures" / "security"
ORACLES = ROOT / "fixtures" / "oracles"
TASKS = {t.task_id: t for t in REGISTRY.tasks}


def _files(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*") if p.is_file() and p.name != ".gitkeep")


def test_every_fixture_task_is_registered_as_development() -> None:
    on_disk = {p.name for d in (SECURITY, ORACLES) for p in d.iterdir() if p.is_dir()}
    assert on_disk == set(TASKS), "every public task is in the registry, and only those"
    assert all(t.split == "development" for t in REGISTRY.tasks), (
        "the public tree is development only"
    )


@pytest.mark.parametrize("task_id", sorted(TASKS))
def test_public_canary_is_in_every_task_file(task_id: str) -> None:
    canary = TASKS[task_id].canary
    files = _files(SECURITY / task_id) + _files(ORACLES / task_id)
    missing = [str(p.relative_to(ROOT)) for p in files if canary not in p.read_text("utf-8")]
    assert not missing, f"canary missing from {missing}"


@pytest.mark.parametrize("task_id", sorted(TASKS))
def test_oracle_canary_is_in_every_oracle_file_and_never_in_the_agent_view(task_id: str) -> None:
    oracle = TASKS[task_id].oracle_canary
    missing = [
        str(p.relative_to(ROOT))
        for p in _files(ORACLES / task_id)
        if oracle not in p.read_text("utf-8")
    ]
    leaked = [
        str(p.relative_to(ROOT))
        for p in _files(SECURITY / task_id)
        if oracle in p.read_text("utf-8")
    ]
    assert not missing, f"oracle canary missing from {missing}"
    assert not leaked, f"oracle canary leaked into agent-visible files {leaked}"


def test_no_oracle_canary_appears_in_any_agent_visible_file() -> None:
    oracles = {t.oracle_canary for t in REGISTRY.tasks}
    for path in _files(SECURITY):
        text = path.read_text("utf-8")
        assert not any(o in text for o in oracles), path


def test_public_tasks_record_exposure_and_overlap() -> None:
    for task in REGISTRY.tasks:
        assert any(e.kind == "public" for e in task.exposure)
        assert task.overlap.strip()


def test_assessment_membership_is_recorded_by_digest_only() -> None:
    raw = (ROOT / "fixtures/dataset.json").read_text("utf-8")
    for member in REGISTRY.assessment:
        assert member.task_identity.startswith("sha256:")
    assert '"split": "assessment"' not in raw  # no assessment content in the public tree
