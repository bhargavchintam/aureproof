# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Croissant 1.1 + RAI metadata and the dataset card (issue #60).

The pinned validator (mlcroissant 1.1.1) runs in the "Croissant" CI workflow;
these tests keep the metadata true to the files it describes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
META = json.loads((FIXTURES / "croissant.json").read_text("utf-8"))
CARD = (FIXTURES / "DATASET_CARD.md").read_text("utf-8")
REGISTRY = json.loads((FIXTURES / "dataset.json").read_text("utf-8"))


def test_metadata_is_committed_exactly_as_generated() -> None:
    spec = importlib.util.spec_from_file_location("cr", ROOT / "scripts/make_croissant.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build() == META  # also catches any fixture edit without regeneration


def test_it_declares_croissant_1_1_and_the_rai_vocabulary() -> None:
    assert META["conformsTo"] == "http://mlcommons.org/croissant/1.1"
    assert META["@context"]["rai"] == "http://mlcommons.org/croissant/RAI/"
    assert META["@context"]["cr"] == "http://mlcommons.org/croissant/"
    for field in (
        "rai:dataCollection",
        "rai:dataCollectionType",
        "rai:dataAnnotationProtocol",
        "rai:dataUseCases",
        "rai:dataLimitations",
        "rai:dataBiases",
        "rai:personalSensitiveInformation",
        "rai:dataReleaseMaintenancePlan",
    ):
        assert META[field], field
    assert META["version"] == REGISTRY["dataset_revision"]
    assert META["license"] == "https://creativecommons.org/licenses/by/4.0/"


def test_every_file_of_every_task_is_pinned_by_its_hash() -> None:
    pinned = {d["contentUrl"]: d["sha256"] for d in META["distribution"]}
    expected = {"dataset.json"}
    for task in (t["task_id"] for t in REGISTRY["tasks"]):
        for base in (FIXTURES / "security" / task, FIXTURES / "oracles" / task):
            expected |= {
                p.relative_to(FIXTURES).as_posix()
                for p in base.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            }
    assert set(pinned) == expected
    for rel, digest in pinned.items():
        assert hashlib.sha256((FIXTURES / rel).read_bytes()).hexdigest() == digest, rel


def test_evaluator_only_files_are_marked_and_no_private_material_is_listed() -> None:
    for d in META["distribution"]:
        if d["contentUrl"].startswith("oracles/"):
            assert d["description"].startswith("Evaluator-only")
    assert REGISTRY["assessment"] == []  # nothing private is registered here
    assert (
        "assessment split" in META["description"]
        and "not part of this release" in META["description"]
    )


def test_the_card_states_use_license_provenance_and_provider_terms() -> None:
    assert "Evaluation only. Never use this data for training" in CARD
    assert "CC-BY-4.0" in CARD and "provider's terms govern them" in CARD
    for task in REGISTRY["tasks"]:
        assert f"`{task['task_id']}`" in CARD
        assert task["exposure"][0]["since"] in CARD
    assert "private" in CARD and "Its labels are never" in CARD
