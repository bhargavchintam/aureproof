# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The matcher, dispositions and metrics must reproduce every golden vector (AP-007)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aureproof.contracts import EpisodeSignals, LabelSet
from aureproof.scoring import (
    MATCHER_VERSION,
    METRICS_VERSION,
    V0_1,
    EpisodeScore,
    compute_metrics,
    score_episode,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN: dict[str, Any] = json.loads(
    (ROOT / "conformance/scoring/v0.1/golden.json").read_text(encoding="utf-8")
)


def submission_bytes(sub: dict[str, Any]) -> bytes | None:
    """Encoding defined in golden.json's ``submission_encoding``."""
    if sub.get("absent"):
        return None
    if "raw" in sub:
        return str(sub["raw"]).encode()
    if "repeat" in sub:
        return json.dumps([sub["repeat"]["finding"]] * sub["repeat"]["count"]).encode()
    return json.dumps(sub["findings"]).encode()


def run_case(case: dict[str, Any]) -> EpisodeScore:
    labels = LabelSet.model_validate(GOLDEN["label_sets"][case["label_set"]])
    assert labels.agent_view is not None
    return score_episode(
        submission_bytes(case["submission"]),
        EpisodeSignals.model_validate(case["signals"]),
        labels,
        variant=case["variant"],
        agent_view=labels.agent_view[case["variant"]],
    )


def test_versions_and_params_match_the_vectors() -> None:
    assert GOLDEN["matcher_version"] == MATCHER_VERSION
    assert GOLDEN["metrics_version"] == METRICS_VERSION
    assert {
        "line_tolerance": V0_1.line_tolerance,
        "max_line_span": V0_1.max_line_span,
        "max_locations": V0_1.max_locations,
        "max_findings": V0_1.max_findings,
        "max_bytes": V0_1.max_bytes,
        "max_depth": V0_1.max_depth,
    } == GOLDEN["params"]


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["id"])
def test_golden_case(case: dict[str, Any]) -> None:
    got = run_case(case)
    expected = case["expected"]
    assert got.disposition.value == expected["disposition"]
    if expected["verdicts"] is None:
        assert got.verdicts is None
    else:
        assert got.verdicts is not None
        assert [
            {
                k: v
                for k, v in r.model_dump(mode="json").items()
                if k in ("verdict", "rule", "defect_id") and v is not None
            }
            for r in got.verdicts
        ] == expected["verdicts"]
        assert all(r.matcher_version == MATCHER_VERSION for r in got.verdicts)
        assert [r.finding_index for r in got.verdicts] == list(range(len(got.verdicts)))
    assert list(got.credited) == expected["credited"]
    assert list(got.annotations) == expected["annotations"]


@pytest.mark.parametrize("cohort", GOLDEN["cohorts"], ids=lambda c: c["id"])
def test_golden_cohort(cohort: dict[str, Any]) -> None:
    by_id = {c["id"]: c for c in GOLDEN["cases"]}
    episodes = [run_case(by_id[i]) for i in cohort["episodes"]]
    metrics = compute_metrics(episodes, cohort=cohort["id"])
    got = {
        name: {"numerator": m.numerator, "denominator": m.denominator}
        for name, m in metrics.items()
    }
    assert got == cohort["expected"]
    for m in metrics.values():
        assert m.metric_version == METRICS_VERSION and m.cohort == cohort["id"]
