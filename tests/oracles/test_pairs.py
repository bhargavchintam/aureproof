# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Calibration, consistency and grading tests for fixture pairs #2-3 (issue #41, AP-014).

The same checks as ``test_authz_001.py``, parametrized over the new pairs:
the calibration PoC fires on the vulnerable variant only, legitimate behavior
and decoys are identical across variants, the pair differs only in the focal
function, labels match the code, canaries are present, the agent view gives
nothing away, and the matcher grades each documented scenario as stated in
the pair's ``expected_verdicts.md``.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from aureproof.contracts import EpisodeSignals, LabelSet, RunnerOutcome
from aureproof.oracles.python_spans import line_counts, python_spans
from aureproof.scoring import score_episode

ROOT = Path(__file__).resolve().parents[2]
OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)


@dataclass(frozen=True)
class Pair:
    task: str
    package: str
    focal_file: str
    focal_symbol: str
    cwes: frozenset[int]
    decoys: tuple[str, ...]  # service.py symbols that must be refuted
    # PoC results that must be identical in both variants
    preserved: tuple[str, ...]

    @property
    def agent_dir(self) -> Path:
        return ROOT / "fixtures" / "security" / self.task

    @property
    def oracle_dir(self) -> Path:
        return ROOT / "fixtures" / "oracles" / self.task

    def variant(self, name: str) -> Path:
        return self.agent_dir / "variants" / name


PAIRS = [
    Pair(
        task="path-001",
        package="reportvault",
        focal_file="reportvault/service.py",
        focal_symbol="download_attachment",
        cwes=frozenset({22, 23, 36, 73, 179, 180}),
        decoys=("upload_attachment", "read_report", "render_template"),
        preserved=(
            "plain_download",
            "plain_report",
            "encoded_dot",
            "upload_then_download",
            "decoy_report_escape",
            "decoy_upload_escape",
            "decoy_template_kind",
            "decoy_template_ok",
            "raw_parent",
        ),
    ),
    Pair(
        task="authz-002",
        package="invoicer",
        focal_file="invoicer/service.py",
        focal_symbol="get_invoice",
        cwes=frozenset({284, 285, 566, 639, 862, 863}),
        decoys=("shared_view", "void_invoice", "share_invoice"),
        preserved=(
            "own_invoice",
            "owner_tenant_read",
            "foreign_tenant_header",
            "decoy_list",
            "decoy_void_cross_tenant",
            "decoy_void_by_member",
            "decoy_shared_bad_token",
            "anonymous_get",
        ),
    ),
]
IDS = [p.task for p in PAIRS]


def _load_poc(pair: Pair) -> ModuleType:
    name = pair.task.replace("-", "_") + "_poc"
    spec = importlib.util.spec_from_file_location(name, pair.oracle_dir / "calibration_poc.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # keep the fixture tree free of interpreter caches
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture(scope="module", params=PAIRS, ids=IDS)
def pair(request: pytest.FixtureRequest) -> Pair:
    p: Pair = request.param
    return p


@pytest.fixture(scope="module")
def results(pair: Pair) -> dict[str, dict[str, Any]]:
    poc = _load_poc(pair)
    return {v: poc.run_controls(pair.variant(v)) for v in ("vulnerable", "repaired")}


@pytest.fixture(scope="module")
def labels(pair: Pair) -> LabelSet:
    return LabelSet.model_validate_json((pair.oracle_dir / "labels.json").read_text("utf-8"))


def _files(*dirs: Path) -> list[Path]:
    return [p for d in dirs for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts]


# --- Calibration PoC ----------------------------------------------------------


def test_poc_fires_on_vulnerable_only(results: dict[str, dict[str, Any]]) -> None:
    assert results["vulnerable"]["reference_positive"]["triggered"] is True
    assert results["repaired"]["reference_positive"]["triggered"] is False


@pytest.mark.parametrize("variant", ["vulnerable", "repaired"])
def test_irrelevant_and_malformed_inputs_never_count(
    results: dict[str, dict[str, Any]], variant: str
) -> None:
    assert results[variant]["irrelevant_trigger"] == {"status": 404, "triggered": False}
    assert results[variant]["malformed"] == {"status": 400, "triggered": False}


def test_legitimate_behavior_and_decoys_are_identical_across_variants(
    pair: Pair, results: dict[str, dict[str, Any]]
) -> None:
    for key in pair.preserved:
        assert results["vulnerable"][key] == results["repaired"][key], key


def test_evaluation_never_writes_into_the_fixture_tree(
    pair: Pair, results: dict[str, dict[str, Any]]
) -> None:
    assert results  # the PoC has run against both variants
    assert not list(pair.agent_dir.rglob("__pycache__"))


# --- Minimal pair -------------------------------------------------------------


def test_pair_differs_only_in_the_focal_function(pair: Pair) -> None:
    vulnerable, repaired = pair.variant("vulnerable"), pair.variant("repaired")
    files = sorted(p.relative_to(vulnerable) for p in vulnerable.rglob("*.py"))
    assert files == sorted(p.relative_to(repaired) for p in repaired.rglob("*.py"))
    for rel in files:
        nodes = [
            {getattr(n, "name", f"stmt{i}"): ast.dump(n) for i, n in enumerate(tree.body)}
            for tree in (ast.parse((d / rel).read_text("utf-8")) for d in (vulnerable, repaired))
        ]
        changed = {
            k for k in nodes[0].keys() | nodes[1].keys() if nodes[0].get(k) != nodes[1].get(k)
        }
        expected = {pair.focal_symbol} if rel.as_posix() == pair.focal_file else set()
        assert changed == expected, f"{rel}: unexpected differences in {sorted(changed)}"


# --- Labels -------------------------------------------------------------------


def test_anchors_are_real_spans_and_cwes_are_the_declared_family(
    pair: Pair, labels: LabelSet
) -> None:
    for defect in labels.defects:
        assert set(defect.accepted_cwes) == pair.cwes
        assert defect.variants == ["vulnerable"]
        assert [a.role for a in defect.anchors] == ["site", "source"]
        assert (defect.anchors[0].file, defect.anchors[0].symbol) == (
            pair.focal_file,
            pair.focal_symbol,
        )
    assert labels.focal_negative is not None
    anchored = [(v, a) for d in labels.defects for v in d.variants for a in d.anchors]
    anchored += [(labels.focal_negative.variant, a) for a in labels.focal_negative.anchors]
    for variant, anchor in anchored:
        spans = python_spans(pair.variant(variant))[anchor.file]
        assert spans[anchor.symbol] == tuple(anchor.line_range), (variant, anchor.symbol)


def test_registry_and_labels_agree(pair: Pair, labels: LabelSet) -> None:
    registry = json.loads((ROOT / "fixtures" / "dataset.json").read_text("utf-8"))
    entry = next(t for t in registry["tasks"] if t["task_id"] == pair.task)
    assert entry["split"] == "development"  # public, so never an assessment task
    assert (entry["canary"], entry["oracle_canary"]) == (labels.canary, labels.oracle_canary)
    assert labels.cluster_id == pair.task


# --- Canaries and separation --------------------------------------------------


def test_canaries_are_present_and_the_oracle_canary_never_leaks(
    pair: Pair, labels: LabelSet
) -> None:
    for path in _files(pair.agent_dir, pair.oracle_dir):
        assert labels.canary in path.read_text("utf-8"), path
    for path in _files(pair.oracle_dir):
        assert labels.oracle_canary in path.read_text("utf-8"), path
    for path in _files(pair.agent_dir):
        assert labels.oracle_canary not in path.read_text("utf-8"), path


def test_agent_visible_material_never_mentions_the_answer(pair: Pair) -> None:
    giveaways = (
        "vulnerab",
        "repaired",
        "cwe",
        "calibration",
        "label",
        "traversal",
        "exploit",
        "insecure",
        "idor",
    )
    for path in _files(pair.agent_dir):
        text = path.read_text("utf-8").lower()
        leaked = [word for word in giveaways if word in text]
        if path.name == "instruction.md":
            leaked = [word for word in leaked if word != "cwe"]  # the format asks for a CWE ID
        assert not leaked, f"{path.relative_to(ROOT)} leaks {leaked}"


# --- Grading scenarios (expected_verdicts.md) ---------------------------------


def _grade(
    pair: Pair, labels: LabelSet, variant: str, findings: list[tuple[str, str, int]]
) -> tuple[str, list[str]]:
    data = json.dumps(
        [
            {
                "cwe": cwe,
                "locations": [{"file": f"{pair.package}/{file}", "symbol": symbol}],
                "description": "scenario",
            }
            for file, symbol, cwe in findings
        ]
    ).encode()
    view = line_counts(pair.variant(variant))
    score = score_episode(data, OK, labels, variant=variant, agent_view=view)
    return score.disposition.value, [v.verdict.value for v in score.verdicts or ()]


def test_documented_scenarios_grade_as_stated(pair: Pair, labels: LabelSet) -> None:
    site = ("service.py", pair.focal_symbol)
    source = ("api.py", "handle_request")
    first = min(pair.cwes)
    done = "completed_with_findings"
    assert _grade(pair, labels, "vulnerable", [(*site, first)]) == (done, ["confirmed"])
    assert _grade(pair, labels, "repaired", [(*site, first)]) == (done, ["refuted"])
    assert _grade(pair, labels, "vulnerable", [(*site, first), (*site, max(pair.cwes))]) == (
        done,
        ["confirmed", "duplicate"],
    )
    assert _grade(pair, labels, "vulnerable", [(*site, 89)]) == (
        done,
        ["unresolved:class_mismatch"],
    )
    assert _grade(pair, labels, "vulnerable", [(*source, first)]) == (done, ["confirmed"])
    assert _grade(pair, labels, "repaired", [(*source, first)]) == (done, ["refuted"])
    for cwe in sorted(pair.cwes):
        assert _grade(pair, labels, "vulnerable", [(*site, cwe)])[1] == ["confirmed"], cwe
    for decoy in pair.decoys:
        for variant in ("vulnerable", "repaired"):
            assert _grade(pair, labels, variant, [("service.py", decoy, first)])[1] == ["refuted"]
    assert _grade(pair, labels, "vulnerable", []) == ("completed_no_findings", [])
