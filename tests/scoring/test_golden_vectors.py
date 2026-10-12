# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Integrity of the scoring golden vectors (issue #9, AP-005).

These tests do not run a matcher (that is AP-007, #15, which must pass every
vector). They keep the vectors well-formed, internally consistent, complete
against the rules and dispositions in ``specs/scoring/scoring.md``, and in sync
with the spec's version numbers and case references.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "scoring" / "scoring.md"
GOLDEN = ROOT / "conformance" / "scoring" / "v0.1" / "golden.json"

RULES = {f"M{n}" for n in range(1, 10)}
DISPOSITIONS = {
    "completed_with_findings",
    "completed_no_findings",
    "invalid_output",
    "safety_refusal",
    "budget_exhausted",
    "agent_error",
    "infra_failure",
    "evidence_incomplete",
}
VERDICTS = {
    "confirmed",
    "duplicate",
    "refuted",
    "unresolved:class_mismatch",
    "unresolved:out_of_scope",
    "invalid",
}
METRICS = {
    "known_defect_recall",
    "adjudicated_precision",
    "unresolved_fraction",
    "strict_confirmed_yield",
    "duplicate_rate",
    "invalid_finding_rate",
    "scoped_false_alarm_rate",
    "operational_completion",
    "refusal_rate",
    "infrastructure_failure_rate",
    "evidence_incomplete_rate",
}


@cache
def golden() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return data


def _submitted(case: dict[str, Any]) -> int | None:
    sub = case["submission"]
    if "findings" in sub:
        return len(sub["findings"])
    if "repeat" in sub:
        return int(sub["repeat"]["count"])
    return None


def test_versions_match_the_spec() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    g = golden()
    assert f"Spec: `{g['spec']}`" in spec
    for key in ("matcher_version", "disposition_version", "metrics_version"):
        assert f'`{key} = "{g[key]}"`' in spec, key


def test_parameters_match_the_spec() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for name, value in golden()["params"].items():
        assert re.search(rf"\| `{name}`[^|]*\| {value:,} \|", spec), name


def test_at_least_fifteen_uniquely_numbered_cases() -> None:
    ids = [c["id"] for c in golden()["cases"]]
    assert len(ids) >= 15
    assert ids == [f"G-{n:02d}" for n in range(1, len(ids) + 1)]


def test_every_rule_disposition_and_verdict_is_exercised() -> None:
    cases = golden()["cases"]
    rules = {v["rule"] for c in cases for v in c["expected"]["verdicts"] or []}
    assert rules == RULES
    assert {c["expected"]["disposition"] for c in cases} == DISPOSITIONS
    verdicts = {v["verdict"] for c in cases for v in c["expected"]["verdicts"] or []}
    assert verdicts == VERDICTS


@pytest.mark.parametrize("case", golden()["cases"], ids=lambda c: c["id"])
def test_case_is_internally_consistent(case: dict[str, Any]) -> None:
    labels = golden()["label_sets"][case["label_set"]]
    expected = case["expected"]
    assert expected["disposition"] in DISPOSITIONS
    present = {d["defect_id"] for d in labels["defects"] if case["variant"] in d["variants"]}
    verdicts = expected["verdicts"]
    if verdicts is None:
        assert expected["credited"] == []
        return
    assert len(verdicts) == _submitted(case) or (verdicts == [] and _submitted(case) is None)
    confirmed = [v["defect_id"] for v in verdicts if v["verdict"] == "confirmed"]
    assert expected["credited"] == confirmed, "credited = confirmed defects in submission order"
    assert len(set(confirmed)) == len(confirmed), "a defect is confirmed at most once"
    for v in verdicts:
        assert v["verdict"] in VERDICTS
        if v["verdict"] in {"confirmed", "duplicate"}:
            assert v["defect_id"] in present
        else:
            assert "defect_id" not in v
        if v["verdict"] == "duplicate":
            assert v["defect_id"] in confirmed


@pytest.mark.parametrize("cohort", golden()["cohorts"], ids=lambda c: c["id"])
def test_cohort_is_well_formed(cohort: dict[str, Any]) -> None:
    case_ids = {c["id"] for c in golden()["cases"]}
    assert set(cohort["episodes"]) <= case_ids
    assert set(cohort["expected"]) == METRICS
    for name, m in cohort["expected"].items():
        assert 0 <= m["numerator"] <= m["denominator"], name


def test_spec_references_only_existing_vectors() -> None:
    g = golden()
    known = {c["id"] for c in g["cases"]} | {c["id"] for c in g["cohorts"]}
    cited = set(re.findall(r"\b[GCS]-\d{2}\b", SPEC.read_text(encoding="utf-8")))
    assert cited <= known, sorted(cited - known)


def test_label_set_passes_its_own_lint() -> None:
    """Rules L1-L4 of scoring.md §2.2 on the synthetic label set."""
    labels = golden()["label_sets"]["g1"]
    anchors = [(d["variants"], a) for d in labels["defects"] for a in d["anchors"]]
    focal = labels["focal_negative"]
    anchors += [([focal["variant"]], a) for a in focal["anchors"]]
    for variants, anchor in anchors:
        for variant in variants:
            view = labels["agent_view"][variant]
            start, end = anchor["line_range"]
            assert anchor["file"] in view and 1 <= start <= end <= view[anchor["file"]]  # L3
            for scope in labels["reviewed_negative_scope"]:  # L2
                if scope["file"] != anchor["file"]:
                    continue
                assert scope.get("symbol") is not None, f"{anchor} inside a whole-file scope"
                assert scope["symbol"].split(".")[-1] != anchor["symbol"].split(".")[-1]
    for defect in labels["defects"]:
        assert defect["accepted_cwes"]  # L4
    # L1: within a file, a final dotted component names exactly one symbol.
    symbols = [(a["file"], a["symbol"]) for _, a in anchors]
    scope = labels["reviewed_negative_scope"]
    symbols += [(s["file"], s["symbol"]) for s in scope if "symbol" in s]
    owner: dict[tuple[str, str], str] = {}
    for file, symbol in symbols:
        assert owner.setdefault((file, symbol.split(".")[-1]), symbol) == symbol, (file, symbol)
