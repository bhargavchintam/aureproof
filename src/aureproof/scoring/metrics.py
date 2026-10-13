# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Cohort metrics (specs/scoring/scoring.md §6): every value keeps its support."""

from __future__ import annotations

from collections.abc import Sequence

from aureproof.contracts.verdicts import Disposition, MetricRecord, VerdictKind
from aureproof.scoring.episode import EpisodeScore
from aureproof.scoring.params import METRICS_VERSION

# Refuted findings *per* reviewed-negative unit: several findings may hit one unit.
RATES = frozenset({"scoped_false_alarm_rate"})
COMPLETED = frozenset({Disposition.COMPLETED_WITH_FINDINGS, Disposition.COMPLETED_NO_FINDINGS})


def compute_metrics(
    episodes: Sequence[EpisodeScore], *, cohort: str | None = None
) -> dict[str, MetricRecord]:
    """Pre-adjudication metrics for one system configuration's scheduled episodes."""
    graded = [e for e in episodes if e.graded]
    verdicts = [r.verdict for e in graded for r in e.verdicts or ()]
    c = verdicts.count(VerdictKind.CONFIRMED)
    r = verdicts.count(VerdictKind.REFUTED)
    dup = verdicts.count(VerdictKind.DUPLICATE)
    inv = verdicts.count(VerdictKind.INVALID)
    unres = sum(
        v in (VerdictKind.UNRESOLVED_CLASS_MISMATCH, VerdictKind.UNRESOLVED_OUT_OF_SCOPE)
        for v in verdicts
    )
    n = len(verdicts)
    e = len(episodes)

    def count(*dispositions: Disposition) -> int:
        return sum(ep.disposition in dispositions for ep in episodes)

    support = {
        "known_defect_recall": (
            sum(len(ep.credited) for ep in graded),
            sum(ep.positives for ep in graded),
        ),
        "adjudicated_precision": (c, c + r),
        "unresolved_fraction": (unres, c + r + unres),
        "strict_confirmed_yield": (c, n),
        "duplicate_rate": (dup, n),
        "invalid_finding_rate": (inv, n),
        "scoped_false_alarm_rate": (r, sum(ep.negative_units for ep in graded)),
        "operational_completion": (count(*COMPLETED), e),
        "refusal_rate": (count(Disposition.SAFETY_REFUSAL), e),
        "infrastructure_failure_rate": (count(Disposition.INFRA_FAILURE), e),
        "evidence_incomplete_rate": (count(Disposition.EVIDENCE_INCOMPLETE), e),
    }
    return {
        name: MetricRecord.of(
            name,
            num,
            den,
            metric_version=METRICS_VERSION,
            cohort=cohort,
            kind="rate" if name in RATES else "proportion",
        )
        for name, (num, den) in support.items()
    }
