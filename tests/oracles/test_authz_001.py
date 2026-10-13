# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Calibration and consistency tests for fixture pair authz-001 (issue #8, AP-010).

These pin the fixture's oracle health before any agent is evaluated on it:
the calibration PoC fires on the vulnerable variant only, legitimate behavior
is preserved, decoys are genuinely safe, the pair differs only in the focal
function, and the evaluator-only labels match the code they point at.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
TASK = "authz-001"
AGENT_DIR = ROOT / "fixtures" / "security" / TASK
ORACLE_DIR = ROOT / "fixtures" / "oracles" / TASK
VARIANTS = {name: AGENT_DIR / "variants" / name for name in ("vulnerable", "repaired")}


def _load_poc() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "authz_001_poc", ORACLE_DIR / "calibration_poc.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # keep the fixture tree free of interpreter caches
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture(scope="module")
def poc() -> ModuleType:
    return _load_poc()


@pytest.fixture(scope="module")
def labels() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ORACLE_DIR / "labels.json").read_text())
    return data


def _fixture_files(*dirs: Path) -> list[Path]:
    """Tracked fixture files: everything except interpreter caches."""
    return [
        path
        for directory in dirs
        for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]


def test_evaluation_never_writes_into_the_fixture_tree(poc: ModuleType) -> None:
    poc.run_controls(VARIANTS["vulnerable"])
    poc.run_controls(VARIANTS["repaired"])
    caches = [p for d in VARIANTS.values() for p in d.rglob("__pycache__")]
    assert not caches, f"evaluation wrote bytecode into the fixture tree: {caches}"


def _function_spans(path: Path) -> dict[str, tuple[int, int]]:
    tree = ast.parse(path.read_text())
    return {
        node.name: (node.lineno, node.end_lineno or node.lineno)
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


# --- Calibration PoC ----------------------------------------------------------


def test_calibration_poc_fires_on_vulnerable_only(poc: ModuleType) -> None:
    assert poc.fires(VARIANTS["vulnerable"]) is True
    assert poc.fires(VARIANTS["repaired"]) is False


@pytest.mark.parametrize("variant", ["vulnerable", "repaired"])
def test_irrelevant_and_malformed_inputs_never_count(poc: ModuleType, variant: str) -> None:
    results = poc.run_controls(VARIANTS[variant])
    assert results["irrelevant_trigger"]["triggered"] is False
    assert results["irrelevant_trigger"]["status"] == 404
    assert results["malformed"]["triggered"] is False
    assert results["malformed"]["status"] == 400


@pytest.mark.parametrize("variant", ["vulnerable", "repaired"])
def test_legitimate_deletes_are_preserved(poc: ModuleType, variant: str) -> None:
    results = poc.run_controls(VARIANTS[variant])
    assert results["owner_delete"]["status"] == 204
    assert results["admin_delete"]["status"] == 204


@pytest.mark.parametrize("variant", ["vulnerable", "repaired"])
def test_decoys_are_safe(poc: ModuleType, variant: str) -> None:
    results = poc.run_controls(VARIANTS[variant])
    assert results["decoy_purge_by_non_admin"]["status"] == 403
    assert results["decoy_public_titles"]["titles"] == ["Release notes"]


# --- Minimal pair -------------------------------------------------------------


def test_pair_differs_only_in_the_focal_function() -> None:
    vulnerable_files = sorted(
        p.relative_to(VARIANTS["vulnerable"]) for p in VARIANTS["vulnerable"].rglob("*.py")
    )
    repaired_files = sorted(
        p.relative_to(VARIANTS["repaired"]) for p in VARIANTS["repaired"].rglob("*.py")
    )
    assert vulnerable_files, "no fixture sources found"
    assert vulnerable_files == repaired_files

    for rel in vulnerable_files:
        vulnerable = ast.parse((VARIANTS["vulnerable"] / rel).read_text())
        repaired = ast.parse((VARIANTS["repaired"] / rel).read_text())
        vulnerable_nodes = {
            getattr(n, "name", f"stmt{i}"): ast.dump(n) for i, n in enumerate(vulnerable.body)
        }
        repaired_nodes = {
            getattr(n, "name", f"stmt{i}"): ast.dump(n) for i, n in enumerate(repaired.body)
        }
        changed = {
            name
            for name in vulnerable_nodes.keys() | repaired_nodes.keys()
            if vulnerable_nodes.get(name) != repaired_nodes.get(name)
        }
        expected = {"delete_document"} if str(rel) == "docstore/service.py" else set()
        assert changed == expected, f"{rel}: unexpected differences in {sorted(changed)}"


# --- Labels stay in sync with the code ----------------------------------------


def test_defect_anchors_point_at_real_spans(labels: dict[str, Any]) -> None:
    for defect in labels["defects"]:
        assert defect["variants"] == ["vulnerable"]
        variant_dir = VARIANTS["vulnerable"]
        for anchor in defect["anchors"]:
            spans = _function_spans(variant_dir / anchor["file"])
            assert anchor["symbol"] in spans, f"{anchor['symbol']} missing in {anchor['file']}"
            assert tuple(anchor["line_range"]) == spans[anchor["symbol"]], (
                f"{anchor['file']}::{anchor['symbol']} label {anchor['line_range']} "
                f"!= code {spans[anchor['symbol']]}"
            )


def test_focal_negative_anchors_point_at_repaired_spans(labels: dict[str, Any]) -> None:
    focal = labels["focal_negative"]
    assert [a["role"] for a in focal["anchors"]] == ["site", "source"]
    for anchor in focal["anchors"]:
        spans = _function_spans(VARIANTS[focal["variant"]] / anchor["file"])
        assert tuple(anchor["line_range"]) == spans[anchor["symbol"]]


def test_reviewed_negative_scope_exists_in_both_variants(labels: dict[str, Any]) -> None:
    for entry in labels["reviewed_negative_scope"]:
        for variant_dir in VARIANTS.values():
            path = variant_dir / entry["file"]
            assert path.is_file(), f"missing {path}"
            if "symbol" in entry:
                assert entry["symbol"] in _function_spans(path)


def test_accepted_cwes_are_the_access_control_family(labels: dict[str, Any]) -> None:
    for defect in labels["defects"]:
        assert set(defect["accepted_cwes"]) == {284, 285, 639, 862}


# --- Canary and separation ----------------------------------------------------


def test_canary_is_present_in_every_fixture_file(labels: dict[str, Any]) -> None:
    canary = labels["canary"]
    files = _fixture_files(AGENT_DIR, ORACLE_DIR)
    assert files
    missing = [str(p.relative_to(ROOT)) for p in files if canary not in p.read_text()]
    assert not missing, f"canary missing from {missing}"


def test_agent_visible_material_never_mentions_the_answer() -> None:
    giveaways = ("vulnerab", "repaired", "cwe", "missing authorization", "calibration", "label")
    files = _fixture_files(AGENT_DIR)
    assert files, "no agent-visible files found"
    for path in files:
        text = path.read_text().lower()
        # Directory names are not mounted into the agent workspace (see oracle README).
        leaked = [word for word in giveaways if word in text]
        if path.name == "instruction.md":
            leaked = [word for word in leaked if word != "cwe"]  # the format asks for a CWE ID
        assert not leaked, f"{path.relative_to(ROOT)} leaks {leaked}"
