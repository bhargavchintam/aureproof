# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Task Health Record v0.1 (specs/thr/README.md, issue #12).

A persistent, machine-readable record that a task's grader works in a named
environment. ``status`` is never asserted by hand: it must equal the status
derived from the required controls and the determinism re-run.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, model_validator

from aureproof.contracts._base import Contract, NonEmptyStr, Variant
from aureproof.contracts.specs import DigestRef, UtcTimestamp, content_identity

THR_VERSION = "0.1"


class ControlKind(StrEnum):
    LABEL_LINT = "label_lint"  # L1-L4 against the code the agent sees
    REFERENCE_POSITIVE = "reference_positive"  # label-perfect submission confirms every defect
    REPAIRED_NEGATIVE = "repaired_negative"  # focal-anchor finding on the repaired variant refuted
    NOP = "nop"  # empty submission: recall 0
    SPRAY_CHEAT = "spray_cheat"  # recall ~1 but strict yield and precision collapse
    MALFORMED = "malformed"  # invalid JSON -> invalid_output
    CALIBRATION_POC = "calibration_poc"  # evaluator PoC fires on vulnerable only


REQUIRED_CONTROLS = frozenset(ControlKind)


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ControlResult(Contract):
    kind: ControlKind
    variant: Variant | None = None
    input_digest: DigestRef
    expected: JsonValue
    observed: JsonValue = None
    passed: bool | None  # None: the control could not run
    run_ids: list[NonEmptyStr] = Field(default_factory=list)
    note: str | None = None


class Determinism(Contract):
    """Every control re-run; outcomes must be identical."""

    rerun_ids: list[NonEmptyStr]
    reproduced: bool | None  # None: the re-run did not happen or could not complete


class Environment(Contract):
    """Health is per environment: an oracle can pass on one backend and fail on another."""

    runner: NonEmptyStr
    runner_version: NonEmptyStr
    image_digest: DigestRef
    platform: NonEmptyStr  # e.g. "linux/amd64"


class ProbeResult(Contract):
    probe: Literal["bandit", "single_shot_model"]
    system_identity: DigestRef
    solved: bool
    detail: str | None = None


class DifficultyProbe(Contract):
    """Does a pattern scanner or a single-shot model already solve the task? (plan C4).

    Optional for health; required before benchmark expansion (M2 gate, issue #44).
    """

    bandit: ProbeResult | None
    single_shot_model: ProbeResult | None


class Reviewer(Contract):
    name: NonEmptyStr
    role: Literal["author", "independent_reviewer"]


class TaskRef(Contract):
    task_id: NonEmptyStr
    task_revision: NonEmptyStr
    task_identity: DigestRef  # TaskSpec.identity


class Provenance(Contract):
    authorship: Literal["self-authored", "authorized-third-party"]
    license: NonEmptyStr


def derive_status(
    controls: list[ControlResult], determinism: Determinism
) -> tuple[HealthStatus, str]:
    """The normative health derivation (specs/thr §3). Returns (status, reason)."""
    by_kind: dict[ControlKind, list[ControlResult]] = {}
    for control in controls:
        by_kind.setdefault(control.kind, []).append(control)
    failed = sorted(k for k, rs in by_kind.items() if any(r.passed is False for r in rs))
    if failed:
        return HealthStatus.UNHEALTHY, "failed controls: " + ", ".join(failed)
    if determinism.reproduced is False:
        return HealthStatus.UNHEALTHY, "the determinism re-run did not reproduce the controls"
    missing = sorted(REQUIRED_CONTROLS - by_kind.keys())
    not_run = sorted(k for k, rs in by_kind.items() if any(r.passed is None for r in rs))
    if missing or not_run:
        return HealthStatus.UNKNOWN, "missing or not run: " + ", ".join(missing + not_run)
    if determinism.reproduced is None:
        return HealthStatus.UNKNOWN, "no determinism re-run"
    return HealthStatus.HEALTHY, "all required controls pass and reproduce"


class TaskHealthRecord(Contract):
    thr_version: Literal["0.1"]
    task: TaskRef
    environment: Environment
    scoring_identity: DigestRef  # the scoring semantics the controls ran under
    controls: Annotated[list[ControlResult], Field(min_length=1)]
    determinism: Determinism
    difficulty_probe: DifficultyProbe | None = None
    status: HealthStatus
    status_reason: NonEmptyStr
    known_limits: list[NonEmptyStr] = Field(default_factory=list)
    reviewed_by: list[Reviewer] = Field(default_factory=list)
    frozen_at: UtcTimestamp | None = None
    canary_id: NonEmptyStr
    provenance: Provenance

    @model_validator(mode="after")
    def _derived_and_reviewed(self) -> Self:
        derived, _ = derive_status(self.controls, self.determinism)
        if self.status is not derived:
            raise ValueError(
                f"status {self.status.value} contradicts the controls ({derived.value})"
            )
        if self.frozen_at is not None and not any(
            r.role == "independent_reviewer" for r in self.reviewed_by
        ):
            raise ValueError("a frozen record names an independent reviewer (ADR-0005)")
        return self


def thr_digest(record: TaskHealthRecord) -> str:
    """What a Decision Protocol's ``cohort[].thr_digest`` names: the THR's canonical JSON."""
    return content_identity(record)
