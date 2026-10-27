# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Episode disposition (specs/scoring/scoring.md §5): exactly one per episode."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from aureproof.contracts.labels import LabelSet
from aureproof.contracts.verdicts import Disposition, EpisodeSignals, RunnerOutcome, VerdictRecord
from aureproof.scoring.matcher import match
from aureproof.scoring.params import V0_1, MatcherParams, scoring_identity
from aureproof.scoring.submission import SubmissionStatus, parse_submission

# Dispositions whose episodes enter quality metrics (§5.3 "Graded").
GRADED = frozenset(
    {
        Disposition.BUDGET_EXHAUSTED,
        Disposition.AGENT_ERROR,
        Disposition.INVALID_OUTPUT,
        Disposition.COMPLETED_WITH_FINDINGS,
        Disposition.COMPLETED_NO_FINDINGS,
    }
)


@dataclass(frozen=True, slots=True)
class EpisodeScore:
    disposition: Disposition
    verdicts: tuple[VerdictRecord, ...] | None  # None: no verdicts were computed
    credited: tuple[str, ...]
    annotations: tuple[str, ...]
    positives: int  # labeled defects present in this episode's variant
    negative_units: int  # reviewed-negative entries (+1 focal on its variant)
    scoring_identity: str  # versions + parameters that produced this score (issue #36)

    @property
    def graded(self) -> bool:
        return self.disposition in GRADED


def score_episode(
    submission: bytes | None,
    signals: EpisodeSignals,
    labels: LabelSet,
    *,
    variant: str,
    agent_view: Mapping[str, int],
    params: MatcherParams = V0_1,
) -> EpisodeScore:
    """Apply the decision list D1-D8 in order; the first match wins."""
    identity = scoring_identity(params)  # raises on unregistered parameters
    positives = sum(variant in d.variants for d in labels.defects)
    focal = labels.focal_negative
    units = len(labels.reviewed_negative_scope) + int(
        focal is not None and focal.variant == variant
    )
    parsed = parse_submission(submission, params)
    empty_or_absent = parsed.status is SubmissionStatus.ABSENT or (
        parsed.status is SubmissionStatus.PARSED and not parsed.findings
    )
    annotations: list[str] = []

    def done(
        disposition: Disposition,
        verdicts: tuple[VerdictRecord, ...] | None = None,
        credited: tuple[str, ...] = (),
    ) -> EpisodeScore:
        return EpisodeScore(
            disposition, verdicts, credited, tuple(annotations), positives, units, identity
        )

    def graded(disposition: Disposition) -> EpisodeScore:
        result = match(
            parsed.findings, labels, variant=variant, agent_view=agent_view, params=params
        )
        return done(disposition, result.verdicts, result.credited)

    outcome = signals.runner_outcome
    if not signals.evidence_complete:  # D1
        return done(Disposition.EVIDENCE_INCOMPLETE)
    if outcome is RunnerOutcome.INFRA_ERROR:  # D2
        return done(Disposition.INFRA_FAILURE)
    if signals.refusal_signal and empty_or_absent:  # D3: never a miss, never retried
        return done(Disposition.SAFETY_REFUSAL)
    if signals.refusal_signal:
        annotations.append("refusal_signal")
    if outcome is RunnerOutcome.LIMIT_EXCEEDED:  # D4: graded on whatever was captured
        if parsed.status is SubmissionStatus.PARSED:
            return graded(Disposition.BUDGET_EXHAUSTED)
        return done(Disposition.BUDGET_EXHAUSTED)
    if outcome is RunnerOutcome.AGENT_ERROR:
        if parsed.status is SubmissionStatus.ABSENT:  # D5
            return done(Disposition.AGENT_ERROR)
        annotations.append("agent_error")
    if parsed.status is not SubmissionStatus.PARSED:  # D6
        return done(Disposition.INVALID_OUTPUT)
    if parsed.findings:  # D7
        return graded(Disposition.COMPLETED_WITH_FINDINGS)
    return graded(Disposition.COMPLETED_NO_FINDINGS)  # D8
