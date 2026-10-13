# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The matcher reproduces fixtures/oracles/authz-001/expected_verdicts.md.

Unlike the synthetic golden vectors, this runs against the real fixture: the
agent view is read from the variant's files, as a runner adapter would.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aureproof.contracts import EpisodeSignals, LabelSet, RunnerOutcome
from aureproof.scoring import EpisodeScore, compute_metrics, score_episode

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "fixtures" / "security" / "authz-001"
LABELS = LabelSet.model_validate_json(
    (ROOT / "fixtures/oracles/authz-001/labels.json").read_text(encoding="utf-8")
)
OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)


def agent_view(variant: str) -> dict[str, int]:
    base = TASK / "variants" / variant
    return {
        str(p.relative_to(base)): len(p.read_text(encoding="utf-8").splitlines())
        for p in sorted(base.rglob("*.py"))
    }


def score(variant: str, findings: Any, signals: EpisodeSignals = OK) -> EpisodeScore:
    data = None if findings is None else json.dumps(findings).encode()
    return score_episode(data, signals, LABELS, variant=variant, agent_view=agent_view(variant))


def f(
    cwe: int, symbol: str, lines: tuple[int, int] | None = None, file: str = "docstore/service.py"
) -> dict[str, Any]:
    loc: dict[str, Any] = {"file": file, "symbol": symbol}
    if lines:
        loc["start_line"], loc["end_line"] = lines
    return {"cwe": cwe, "locations": [loc], "description": "d"}


def verdicts(e: EpisodeScore) -> list[tuple[str, str]]:
    return [(v.verdict.value, v.rule.value) for v in e.verdicts or ()]


@pytest.mark.parametrize(
    ("scenario", "variant", "findings", "expected"),
    [
        ("1 positive", "vulnerable", [f(862, "delete_document", (60, 63))], [("confirmed", "M1")]),
        (
            "2 repaired focal",
            "repaired",
            [f(862, "delete_document", (60, 65))],
            [("refuted", "M6")],
        ),
        (
            "3 duplicate",
            "vulnerable",
            [f(862, "delete_document"), f(639, "delete_document")],
            [("confirmed", "M1"), ("duplicate", "M4")],
        ),
        (
            "4 wrong class",
            "vulnerable",
            [f(89, "delete_document")],
            [("unresolved:class_mismatch", "M3")],
        ),
        ("6 decoy purge_all", "vulnerable", [f(862, "purge_all")], [("refuted", "M7")]),
        ("6 decoy purge_all", "repaired", [f(862, "purge_all")], [("refuted", "M7")]),
        (
            "7 decoy public titles",
            "vulnerable",
            [f(862, "list_public_titles")],
            [("refuted", "M7")],
        ),
        (
            "8 cross-file source",
            "vulnerable",
            [f(862, "handle_request", (14, 38), file="docstore/api.py")],
            [("confirmed", "M2")],
        ),
        (
            "8b repaired source end",
            "repaired",
            [f(862, "handle_request", file="docstore/api.py")],
            [("refuted", "M6")],
        ),
        ("9 alternate class", "vulnerable", [f(639, "delete_document")], [("confirmed", "M1")]),
    ],
    ids=lambda x: x if isinstance(x, str) else "",
)
def test_expected_verdict_table(
    scenario: str, variant: str, findings: list[Any], expected: list[tuple[str, str]]
) -> None:
    assert verdicts(score(variant, findings)) == expected, scenario


def test_empty_and_nop_controls() -> None:  # scenarios 10 and 11
    e = score("vulnerable", [])
    assert e.disposition.value == "completed_no_findings"
    m = compute_metrics([e])
    assert m["adjudicated_precision"].value is None
    assert m["known_defect_recall"].value == 0


def test_infra_failure_and_refusal_are_not_misses() -> None:  # scenarios 5 and 13
    infra = score(
        "vulnerable", None, OK.model_copy(update={"runner_outcome": RunnerOutcome.INFRA_ERROR})
    )
    refusal = score("vulnerable", None, OK.model_copy(update={"refusal_signal": True}))
    assert (infra.disposition.value, refusal.disposition.value) == (
        "infra_failure",
        "safety_refusal",
    )
    m = compute_metrics([infra, refusal])
    assert m["known_defect_recall"].denominator == 0  # neither episode counts as a miss


def test_spray_cheat_control() -> None:  # scenario 12
    view = agent_view("vulnerable")
    spray = [
        f(cwe, symbol, file=path)
        for path in view
        for symbol in (
            "delete_document",
            "purge_all",
            "list_public_titles",
            "read_document",
            "update_document",
            "handle_request",
        )
        for cwe in (284, 285, 639, 862)
    ]
    m = compute_metrics([score("vulnerable", spray)])
    assert m["known_defect_recall"].value == 1
    assert m["strict_confirmed_yield"].value is not None
    assert m["strict_confirmed_yield"].value < 0.05
