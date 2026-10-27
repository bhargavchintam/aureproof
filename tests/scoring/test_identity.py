# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Scoring semantics are bound to a version identity (issue #36)."""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from aureproof.contracts import EpisodeSignals, LabelSet, MetricRecord, RunnerOutcome
from aureproof.scoring import (
    MATCHER_VERSION,
    PROFILES,
    V0_1,
    MatcherParams,
    UnregisteredParams,
    match,
    parse_submission,
    score_episode,
    scoring_identity,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((ROOT / "conformance/scoring/v0.1/golden.json").read_text("utf-8"))
G1 = LabelSet.model_validate(GOLDEN["label_sets"]["g1"])
assert G1.agent_view is not None
VIEW = G1.agent_view["vulnerable"]
OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)
FINDING = [
    {"cwe": 89, "locations": [{"file": "app/orders.py", "start_line": 47}], "description": "d"}
]


def test_the_golden_vectors_pin_the_scoring_identity() -> None:
    assert GOLDEN["scoring_identity"] == scoring_identity()
    assert PROFILES == {MATCHER_VERSION: V0_1}


@pytest.mark.parametrize("field", [f.name for f in dataclasses.fields(MatcherParams)])
def test_every_parameter_is_part_of_the_identity_and_overrides_are_rejected(field: str) -> None:
    changed = dataclasses.replace(V0_1, **{field: getattr(V0_1, field) + 1})
    with pytest.raises(UnregisteredParams):
        scoring_identity(changed)
    with pytest.raises(UnregisteredParams):
        match(FINDING, G1, variant="vulnerable", agent_view=VIEW, params=changed)
    with pytest.raises(UnregisteredParams):
        score_episode(
            json.dumps(FINDING).encode(),
            OK,
            G1,
            variant="vulnerable",
            agent_view=VIEW,
            params=changed,
        )
    with pytest.raises(UnregisteredParams):
        parse_submission(b"[]", changed)


def test_the_audit_case_a_widened_tolerance_cannot_claim_version_0_1_0() -> None:
    """line_tolerance=100 used to change a verdict while recording matcher 0.1.0."""
    with pytest.raises(UnregisteredParams):
        match(
            FINDING,
            G1,
            variant="vulnerable",
            agent_view=VIEW,
            params=MatcherParams(line_tolerance=100),
        )


def test_scored_episodes_carry_their_identity_and_rescore_identically() -> None:
    data = json.dumps(FINDING).encode()
    first = score_episode(data, OK, G1, variant="vulnerable", agent_view=VIEW)
    again = score_episode(data, OK, G1, variant="vulnerable", agent_view=VIEW)
    assert first.scoring_identity == scoring_identity() == again.scoring_identity
    assert first == again


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_defined_metric_values_are_finite(bad: float) -> None:
    with pytest.raises(ValidationError):
        MetricRecord(metric="m", numerator=1, denominator=2, value=bad, metric_version="0.1.0")


def test_metric_values_agree_within_the_documented_tolerance() -> None:
    MetricRecord(
        metric="m", numerator=1, denominator=3, value=1 / 3 + 1e-14, metric_version="0.1.0"
    )
    with pytest.raises(ValidationError):
        MetricRecord(
            metric="m", numerator=1, denominator=3, value=1 / 3 + 1e-9, metric_version="0.1.0"
        )
