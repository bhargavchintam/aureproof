# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Evaluator-only defect labels (specs/scoring/scoring.md §2.2).

Labels never enter an agent's build context. Cross-reference lint (L1-L3:
unique symbols, anchors outside reviewed scope, anchors inside the agent view)
is a task-health check; this module enforces what a single label set can
guarantee on its own (shape, L4, unique defect IDs).
"""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from aureproof.contracts._base import (
    Contract,
    NonEmptyStr,
    NonNegativeInt,
    PositiveInt,
    StrictBool,
    Variant,
)
from aureproof.contracts.findings import Role

LineRange = tuple[PositiveInt, PositiveInt]


def _ordered(line_range: tuple[int, int] | None) -> None:
    if line_range is not None and line_range[1] < line_range[0]:
        raise ValueError("line_range must be [start, end] with start <= end")


class Anchor(Contract):
    file: NonEmptyStr
    symbol: NonEmptyStr
    line_range: LineRange
    role: Role = Role.SITE
    role_required: StrictBool = False

    @model_validator(mode="after")
    def _range(self) -> Self:
        _ordered(self.line_range)
        return self


class Defect(Contract):
    defect_id: NonEmptyStr
    variants: Annotated[list[Variant], Field(min_length=1)]
    accepted_cwes: Annotated[list[PositiveInt], Field(min_length=1)]  # L4
    anchors: Annotated[list[Anchor], Field(min_length=1)]
    summary: str | None = None
    calibration_poc: str | None = None


class FocalNegative(Contract):
    """Where the repaired defect used to be: every anchor of it (site and ends)."""

    variant: Variant
    anchors: Annotated[list[Anchor], Field(min_length=1)]


class ScopeEntry(Contract):
    """Reviewed and found free of in-scope defects. No symbol = the whole file."""

    file: NonEmptyStr
    symbol: NonEmptyStr | None = None
    line_range: LineRange | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _range(self) -> Self:
        _ordered(self.line_range)
        return self


class LabelSet(Contract):
    label_schema: str | None = Field(default=None, alias="schema")
    label_set: NonEmptyStr | None = None
    task_id: NonEmptyStr | None = None
    task_revision: NonEmptyStr | None = None
    cluster_id: NonEmptyStr | None = None
    canary: NonEmptyStr | None = None
    oracle_canary: NonEmptyStr | None = None  # evaluator-only leak marker (#45)
    note: str | None = None
    agent_view: dict[Variant, dict[str, NonNegativeInt]] | None = None
    defects: list[Defect]
    focal_negative: FocalNegative | None = None
    reviewed_negative_scope: list[ScopeEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        ids = [d.defect_id for d in self.defects]
        if len(ids) != len(set(ids)):
            raise ValueError("defect_id values must be unique")
        return self
