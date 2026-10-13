# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Label, verdict, disposition, metric and event contracts (AP-004)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from aureproof.contracts import (
    Disposition,
    EpisodeSignals,
    Event,
    FindingsSubmission,
    LabelSet,
    MetricRecord,
    ObservationSource,
    PocRefSubmission,
    Rule,
    Submission,
    VerdictKind,
    VerdictRecord,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((ROOT / "conformance/scoring/v0.1/golden.json").read_text(encoding="utf-8"))
SHA = "a" * 64


def test_golden_label_set_is_a_valid_label_set() -> None:
    labels = LabelSet.model_validate(GOLDEN["label_sets"]["g1"])
    assert [d.defect_id for d in labels.defects] == ["g1-d1", "g1-d2", "g1-d3"]
    assert labels.defects[2].anchors[0].role_required


def test_authz_001_labels_are_a_valid_label_set() -> None:
    raw = json.loads((ROOT / "fixtures/oracles/authz-001/labels.json").read_text(encoding="utf-8"))
    labels = LabelSet.model_validate(raw)
    assert labels.focal_negative is not None
    assert len(labels.focal_negative.anchors) == 2  # site and source (scoring.md Q6)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda g: g["defects"][0].update(accepted_cwes=[]),  # L4
        lambda g: g["defects"][0].update(variants=[]),
        lambda g: g["defects"][0].update(variants=["patched"]),
        lambda g: g["defects"][0]["anchors"][0].update(line_range=[44, 40]),
        lambda g: g["defects"][0]["anchors"][0].update(line_range=[0, 4]),
        lambda g: g["defects"][0].update(anchors=[]),
        lambda g: g["defects"].append(dict(g["defects"][0])),  # duplicate defect_id
        lambda g: g.update(unexpected=True),
    ],
)
def test_invalid_label_sets(mutate: Any) -> None:
    g = json.loads(json.dumps(GOLDEN["label_sets"]["g1"]))
    mutate(g)
    with pytest.raises(ValidationError):
        LabelSet.model_validate(g)


def test_verdict_vocabulary_matches_the_spec() -> None:
    assert {v.value for v in VerdictKind} == {
        "confirmed",
        "duplicate",
        "refuted",
        "unresolved:class_mismatch",
        "unresolved:out_of_scope",
        "invalid",
    }
    assert {r.value for r in Rule} == {f"M{n}" for n in range(1, 10)}


def test_dispositions_include_safety_refusal_and_match_golden() -> None:
    assert Disposition.SAFETY_REFUSAL.value == "safety_refusal"
    assert {c["expected"]["disposition"] for c in GOLDEN["cases"]} == {d.value for d in Disposition}


def test_golden_verdicts_and_signals_parse() -> None:
    for case in GOLDEN["cases"]:
        EpisodeSignals.model_validate(case["signals"])
        for i, v in enumerate(case["expected"]["verdicts"] or []):
            VerdictRecord.model_validate({**v, "finding_index": i, "matcher_version": "0.1.0"})


def test_confirmed_and_duplicate_need_a_defect_and_others_forbid_one() -> None:
    base = {"finding_index": 0, "matcher_version": "0.1.0"}
    with pytest.raises(ValidationError):
        VerdictRecord.model_validate({**base, "verdict": "confirmed", "rule": "M1"})
    with pytest.raises(ValidationError):
        VerdictRecord.model_validate(
            {**base, "verdict": "refuted", "rule": "M7", "defect_id": "d1"}
        )


def test_metric_record_value_is_null_exactly_when_undefined() -> None:
    m = MetricRecord.of("strict_confirmed_yield", 3, 10, metric_version="0.1.0")
    assert m.value == pytest.approx(0.3) and m.undefined_reason is None
    u = MetricRecord.of("adjudicated_precision", 0, 0, metric_version="0.1.0")
    assert u.value is None and u.undefined_reason == "denominator is 0"
    with pytest.raises(ValidationError):
        MetricRecord.of("x", 4, 3, metric_version="0.1.0")


def test_events_carry_a_trust_tier() -> None:
    assert {s.value for s in ObservationSource} == {
        "controller_observed",
        "agent_reported",
        "imported",
    }
    e = Event.model_validate(
        {
            "seq": 0,
            "episode_id": "ep-1",
            "actor": "runner",
            "kind": "model_call",
            "observation_source": "controller_observed",
            "blob_refs": [f"sha256:{SHA}"],
        }
    )
    assert e.observation_source is ObservationSource.CONTROLLER_OBSERVED
    with pytest.raises(ValidationError):
        Event.model_validate({**e.model_dump(), "blob_refs": ["md5:abc"]})
    with pytest.raises(ValidationError):
        Event.model_validate({**e.model_dump(), "seq": -1})


def test_submission_is_a_tagged_union() -> None:
    from pydantic import TypeAdapter

    adapter: TypeAdapter[Submission] = TypeAdapter(Submission)
    f = adapter.validate_python({"kind": "findings", "sha256": SHA, "size_bytes": 2})
    p = adapter.validate_python({"kind": "poc_ref", "sha256": SHA, "executed": False})
    assert isinstance(f, FindingsSubmission) and isinstance(p, PocRefSubmission)
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "patch", "sha256": SHA})
    with pytest.raises(ValidationError):  # v0.1 never executes agent PoCs (ADR-0004)
        adapter.validate_python({"kind": "poc_ref", "sha256": SHA, "executed": True})
