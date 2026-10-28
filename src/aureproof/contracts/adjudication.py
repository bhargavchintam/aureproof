# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Adjudication records (issue #51; plan §5.7; specs/adjudication).

An adjudication is a recorded grading operation on one unresolved finding of one
sealed bundle: who decided what, why, on which evidence, under which dataset
revision. Records are append-only. Re-adjudicating adds a record and never
edits one, and the bundle itself is never touched.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, NonNegativeInt, model_validator

from aureproof.contracts._base import Contract, NonEmptyStr
from aureproof.contracts.specs import DigestRef, UtcTimestamp, content_identity

UNRESOLVED = ("unresolved:class_mismatch", "unresolved:out_of_scope")


class Decision(StrEnum):
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    LABEL_CHANGE = "label_change"  # the labels are wrong: a new dataset revision


class Role(StrEnum):
    PRIMARY = "primary"
    SECOND = "second"  # independent second adjudicator, for agreement
    RESOLUTION = "resolution"  # settles a disagreement between primary and second


class FindingRef(Contract):
    episode_id: NonEmptyStr
    finding_index: NonNegativeInt


class Adjudication(Contract):
    adjudication_version: Literal["0.1"] = "0.1"
    bundle_seal: DigestRef  # sha256 of the sealed bundle's seal.intoto.json
    finding: FindingRef
    original_verdict: Literal["unresolved:class_mismatch", "unresolved:out_of_scope"]
    adjudicator: NonEmptyStr
    role: Role = Role.PRIMARY
    decision: Decision
    rationale: NonEmptyStr
    evidence_refs: list[NonEmptyStr] = Field(default_factory=list)
    timestamp: UtcTimestamp
    dataset_revision_before: NonEmptyStr
    dataset_revision_after: NonEmptyStr

    @model_validator(mode="after")
    def _revision_moves_only_on_label_change(self) -> Self:
        moved = self.dataset_revision_after != self.dataset_revision_before
        if moved != (self.decision is Decision.LABEL_CHANGE):
            raise ValueError(
                "a label_change needs a new dataset revision, and only a label_change has one"
            )
        return self

    @property
    def identity(self) -> str:
        return content_identity(self)
