# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Explicit migrations and `aureproof migrate` (issue #58)."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aureproof.bundle.canonical import digest_ref
from aureproof.cli.main import app
from aureproof.contracts.labels import LabelSet
from aureproof.contracts.migrate import MigrationError, migrate

ROOT = Path(__file__).resolve().parents[2]
VECTOR = ROOT / "conformance" / "migrations" / "labels-draft-0-to-v0.1"
TUTORIAL = ROOT / "examples" / "bundles" / "tutorial-v0.1"
cli = CliRunner()


def _load(name: str) -> dict:  # type: ignore[type-arg]
    data: dict = json.loads((VECTOR / name).read_text("utf-8"))  # type: ignore[type-arg]
    return data


def test_producer_matches_the_vector_and_declares_its_losses() -> None:
    result = migrate(_load("input.json"))
    assert result.record == _load("expected.json")
    assert result.losses == _load("losses.json")
    assert (result.source_version, result.target_version) == (
        "aureproof.labels/draft-0",
        "aureproof.labels/v0.1",
    )


def test_consumer_reads_the_migrated_labels() -> None:
    labels = LabelSet.model_validate(_load("expected.json"))
    assert labels.defects[0].variants == ["vulnerable"]
    assert labels.focal_negative is not None and len(labels.focal_negative.anchors) == 1


def test_the_migration_differs_from_the_hand_migration_only_by_the_declared_loss() -> None:
    """The real N-1 history: d85a543 (draft-0) was migrated by hand in d417444."""
    hand, automatic = _load("hand-migrated-d417444.json"), _load("expected.json")
    assert [a["role"] for a in hand["focal_negative"]["anchors"]] == ["site", "source"]
    without_source = copy.deepcopy(hand)
    without_source["focal_negative"]["anchors"] = hand["focal_negative"]["anchors"][:1]
    assert automatic == without_source


def test_the_input_is_never_modified() -> None:
    data = _load("input.json")
    before = copy.deepcopy(data)
    migrate(data)
    assert data == before


@pytest.mark.parametrize(
    ("record", "message"),
    [
        ({"schema": "aureproof.labels/v0.1"}, "already the current version"),
        ({"schema": "aureproof.labels/v9"}, "no migration from 'aureproof.labels/v9'"),
        ({"no": "schema"}, "no migration from None"),
        ([], "must be a JSON object"),
    ],
)
def test_unknown_and_current_versions_are_refused_by_name(record: object, message: str) -> None:
    with pytest.raises(MigrationError, match=message):
        migrate(record)


def test_cli_writes_a_new_file_with_provenance(tmp_path: Path) -> None:
    out = tmp_path / "labels.json"
    result = cli.invoke(app, ["migrate", str(VECTOR / "input.json"), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "loss: focal_negative" in result.output
    assert json.loads(out.read_text()) == _load("expected.json")
    provenance = json.loads((tmp_path / "labels.json.provenance.json").read_text())
    assert provenance["migrated_from"]["sha256"] == digest_ref((VECTOR / "input.json").read_bytes())
    assert provenance["losses"] == _load("losses.json")
    again = cli.invoke(app, ["migrate", str(VECTOR / "input.json"), "--out", str(out)])
    assert again.exit_code == 2  # never overwrites


def test_cli_never_migrates_sealed_evidence(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(TUTORIAL, bundle)
    for target in (bundle, bundle / "tasks" / "g1" / "labels.json"):
        result = cli.invoke(app, ["migrate", str(target), "--out", str(tmp_path / "x.json")])
        assert result.exit_code == 2 and "sealed evidence is never migrated" in result.output
