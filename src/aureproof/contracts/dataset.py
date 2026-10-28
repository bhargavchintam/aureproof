# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Dataset registry: splits, revisions, canaries, exposure (issue #45, plan v2 §7.6).

The public registry records assessment-split membership only by task identity
digest, before the assessment, so membership is fixed in advance without
revealing assessment content.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from aureproof.contracts._base import Contract, NonEmptyStr
from aureproof.contracts.specs import DigestRef, UtcTimestamp

Guid = Annotated[
    str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
]


class Exposure(Contract):
    since: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    where: NonEmptyStr
    kind: Literal["public", "private"]


class RegisteredTask(Contract):
    task_id: NonEmptyStr
    split: Literal["development", "assessment"]
    task_revision: NonEmptyStr
    canary: Guid  # in every file of the task, agent-visible ones included
    oracle_canary: Guid  # in every evaluator-only file and in no agent-visible file
    exposure: Annotated[list[Exposure], Field(min_length=1)]
    overlap: NonEmptyStr  # known overlap with public benchmarks or textbook patterns

    @model_validator(mode="after")
    def _distinct(self) -> Self:
        if self.canary == self.oracle_canary:
            raise ValueError("the oracle canary must differ from the public canary")
        if self.split == "assessment" and any(e.kind == "public" for e in self.exposure):
            raise ValueError("an exposed task cannot be an assessment task")
        return self


class AssessmentMember(Contract):
    task_identity: DigestRef  # TaskSpec.identity; no content is published
    registered_at: UtcTimestamp


class DatasetRegistry(Contract):
    dataset_id: NonEmptyStr
    dataset_revision: NonEmptyStr
    tasks: list[RegisteredTask]
    assessment_repository: NonEmptyStr  # where the private split lives (name only)
    # Public registry only: assessment membership by digest, registered before assessment.
    assessment: list[AssessmentMember] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique(self) -> Self:
        ids = [t.task_id for t in self.tasks]
        guids = [g for t in self.tasks for g in (t.canary, t.oracle_canary)]
        members = [m.task_identity for m in self.assessment]
        if len(ids) != len(set(ids)) or len(guids) != len(set(guids)):
            raise ValueError("task IDs and canaries must be unique")
        if len(members) != len(set(members)):
            raise ValueError("assessment members must be unique")
        return self
