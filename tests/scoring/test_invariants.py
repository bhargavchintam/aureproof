# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Property-based invariants of the matcher and metrics (issue #15)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from aureproof.contracts import Disposition, EpisodeSignals, LabelSet, RunnerOutcome
from aureproof.scoring import compute_metrics, match, score_episode

ROOT = Path(__file__).resolve().parents[2]
G1 = LabelSet.model_validate(
    json.loads((ROOT / "conformance/scoring/v0.1/golden.json").read_text(encoding="utf-8"))[
        "label_sets"
    ]["g1"]
)
assert G1.agent_view is not None
VIEW = G1.agent_view["vulnerable"]
SYMBOLS = [
    "find_orders",
    "order_total",
    "run_report",
    "search",
    "list_orders",
    "purge",
    "helper",
    "export",
    "app.orders.find_orders",
]
CWES = [89, 943, 78, 79, 862, 22, "CWE-89"]
OK = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.OK)


@st.composite
def locations(draw: st.DrawFn) -> dict[str, Any]:
    file = draw(st.sampled_from(sorted(VIEW)))
    loc: dict[str, Any] = {"file": file}
    if draw(st.booleans()):
        loc["symbol"] = draw(st.sampled_from(SYMBOLS))
    if "symbol" not in loc or draw(st.booleans()):
        start = draw(st.integers(1, VIEW[file]))
        loc["start_line"] = start
        loc["end_line"] = draw(st.integers(start, min(VIEW[file], start + 40)))
    loc["role"] = draw(st.sampled_from(["site", "source", "sink"]))
    return loc


findings = st.lists(
    st.fixed_dictionaries(
        {
            "cwe": st.sampled_from(CWES),
            "locations": st.lists(locations(), min_size=1, max_size=3),
            "description": st.just("d"),
        }
    ),
    max_size=12,
)
variants = st.sampled_from(["vulnerable", "repaired"])


def credited(raw: list[Any], variant: str) -> tuple[str, ...]:
    return match(raw, G1, variant=variant, agent_view=VIEW).credited


@settings(max_examples=300)
@given(findings, variants, st.data())
def test_duplicates_never_change_recall(raw: list[Any], variant: str, data: st.DataObject) -> None:
    if not raw:
        return
    i = data.draw(st.integers(0, len(raw) - 1))
    before = credited(raw, variant)
    assert credited([*raw, raw[i]], variant) == before  # repeat at the end
    assert credited([*raw[: i + 1], raw[i], *raw[i + 1 :]], variant) == before  # repeat in place


@settings(max_examples=300)
@given(findings, variants)
def test_matcher_is_deterministic_and_total(raw: list[Any], variant: str) -> None:
    a = match(raw, G1, variant=variant, agent_view=VIEW)
    b = match(json.loads(json.dumps(raw)), G1, variant=variant, agent_view=VIEW)
    assert a == b
    assert len(a.verdicts) == len(raw)
    confirmed = [v.defect_id for v in a.verdicts if v.verdict == "confirmed"]
    assert tuple(confirmed) == a.credited
    present = {d.defect_id for d in G1.defects if variant in d.variants}
    assert set(a.credited) <= present


@settings(max_examples=200)
@given(st.lists(st.tuples(findings, variants), min_size=1, max_size=5))
def test_precision_undefined_iff_no_confirmed_or_refuted(cohort: list[Any]) -> None:
    episodes = [
        score_episode(json.dumps(raw).encode(), OK, G1, variant=v, agent_view=VIEW)
        for raw, v in cohort
    ]
    metrics = compute_metrics(episodes)
    verdicts = [r.verdict for e in episodes for r in e.verdicts or []]
    c, r = verdicts.count("confirmed"), verdicts.count("refuted")
    precision = metrics["adjudicated_precision"]
    assert (precision.value is None) == (c + r == 0)
    assert metrics["strict_confirmed_yield"].numerator == c
    assert metrics["known_defect_recall"].numerator == sum(len(e.credited) for e in episodes)
    for m in metrics.values():
        assert m.kind == "rate" or m.numerator <= m.denominator


def _spray() -> list[dict[str, Any]]:
    """One finding per (file, every 10-line block) with every accepted CWE."""
    cwes = sorted({c for d in G1.defects for c in d.accepted_cwes})
    return [
        {
            "cwe": cwe,
            "locations": [{"file": f, "start_line": s, "end_line": min(n, s + 9)}],
            "description": "spray",
        }
        for f, n in sorted(VIEW.items())
        for s in range(1, n + 1, 10)
        for cwe in cwes
    ]


def test_spray_control_collapses_strict_confirmed_yield() -> None:
    """THR spray_cheat: recall goes up, but no headline metric rewards spraying."""
    episode = score_episode(
        json.dumps(_spray()).encode(), OK, G1, variant="vulnerable", agent_view=VIEW
    )
    assert episode.disposition is Disposition.COMPLETED_WITH_FINDINGS
    m = compute_metrics([episode])
    honest = compute_metrics(
        [
            score_episode(
                json.dumps(
                    [
                        {
                            "cwe": 89,
                            "locations": [{"file": "app/orders.py", "symbol": "find_orders"}],
                            "description": "sqli",
                        }
                    ]
                ).encode(),
                OK,
                G1,
                variant="vulnerable",
                agent_view=VIEW,
            )
        ]
    )
    assert m["known_defect_recall"].value is not None and m["known_defect_recall"].value >= 2 / 3
    assert m["strict_confirmed_yield"].value is not None
    assert m["strict_confirmed_yield"].value <= 0.05
    assert honest["strict_confirmed_yield"].value == 1.0
    precision = m["adjudicated_precision"].value
    assert precision is not None and precision < honest["adjudicated_precision"].value  # type: ignore[operator]
