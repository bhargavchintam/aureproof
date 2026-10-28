# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Verdicts, episode dispositions, signals and metric records (scoring.md §4-§6)."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Literal, Self

from pydantic import model_validator

from aureproof.contracts._base import Contract, NonEmptyStr, NonNegativeInt, StrictBool


class VerdictKind(StrEnum):
    CONFIRMED = "confirmed"
    DUPLICATE = "duplicate"
    REFUTED = "refuted"
    UNRESOLVED_CLASS_MISMATCH = "unresolved:class_mismatch"
    UNRESOLVED_OUT_OF_SCOPE = "unresolved:out_of_scope"
    INVALID = "invalid"


class Rule(StrEnum):
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"
    M6 = "M6"
    M7 = "M7"
    M8 = "M8"
    M9 = "M9"


class Disposition(StrEnum):
    """Exactly one per scheduled episode (scoring.md §5.3, D1-D8)."""

    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    INFRA_FAILURE = "infra_failure"
    SAFETY_REFUSAL = "safety_refusal"
    BUDGET_EXHAUSTED = "budget_exhausted"
    AGENT_ERROR = "agent_error"
    INVALID_OUTPUT = "invalid_output"
    COMPLETED_WITH_FINDINGS = "completed_with_findings"
    COMPLETED_NO_FINDINGS = "completed_no_findings"


class RunnerOutcome(StrEnum):
    OK = "ok"
    INFRA_ERROR = "infra_error"
    AGENT_ERROR = "agent_error"
    LIMIT_EXCEEDED = "limit_exceeded"


class EpisodeSignals(Contract):
    """Controller-observed episode facts; never agent-reported (scoring.md §5.1)."""

    evidence_complete: StrictBool
    runner_outcome: RunnerOutcome
    refusal_signal: StrictBool = False


class MatchInfo(Contract):
    kind: Literal["symbol", "line"]
    anchor_index: NonNegativeInt


class VerdictRecord(Contract):
    finding_index: NonNegativeInt
    verdict: VerdictKind
    rule: Rule
    defect_id: NonEmptyStr | None = None
    match: MatchInfo | None = None
    matcher_version: NonEmptyStr

    @model_validator(mode="after")
    def _defect_only_when_credited(self) -> Self:
        credited = self.verdict in (VerdictKind.CONFIRMED, VerdictKind.DUPLICATE)
        if credited != (self.defect_id is not None):
            raise ValueError(
                "defect_id is required for confirmed/duplicate and forbidden otherwise"
            )
        return self


# Relative tolerance between value and numerator/denominator (scoring.md §6).
METRIC_TOLERANCE = 1e-12


class MetricRecord(Contract):
    """Every percentage keeps its support; ``value`` is null iff the denominator is 0."""

    metric: NonEmptyStr
    kind: Literal["proportion", "rate"] = "proportion"  # a rate may exceed 1
    numerator: NonNegativeInt
    denominator: NonNegativeInt
    value: float | None
    undefined_reason: str | None = None
    cohort: str | None = None
    metric_version: NonEmptyStr

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.kind == "proportion" and self.numerator > self.denominator:
            raise ValueError("a proportion's numerator must not exceed its denominator")
        if (self.denominator == 0) != (self.value is None):
            raise ValueError("value must be null exactly when the denominator is 0")
        if (self.value is None) != (self.undefined_reason is not None):
            raise ValueError("undefined_reason is required exactly when value is null")
        if self.value is not None:
            expected = self.numerator / self.denominator
            if not math.isfinite(self.value):
                raise ValueError("a defined metric value must be finite")
            if abs(self.value - expected) > METRIC_TOLERANCE * max(1.0, abs(expected)):
                raise ValueError("value does not equal numerator / denominator")
        return self

    @classmethod
    def of(
        cls,
        metric: str,
        numerator: int,
        denominator: int,
        *,
        metric_version: str,
        cohort: str | None = None,
        kind: Literal["proportion", "rate"] = "proportion",
    ) -> MetricRecord:
        defined = denominator > 0
        return cls(
            metric=metric,
            kind=kind,
            numerator=numerator,
            denominator=denominator,
            value=numerator / denominator if defined else None,
            undefined_reason=None if defined else "denominator is 0",
            cohort=cohort,
            metric_version=metric_version,
        )
