# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Evidence events and submissions (plan v2 §3.5, §3.7).

The journal format (hash chain, sealing) is specified by the Evidence Bundle
spec (AP-036); these are the records it carries.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import Field

from aureproof.contracts._base import BlobRef, Contract, NonEmptyStr, NonNegativeInt, Sha256Hex


class ObservationSource(StrEnum):
    """Trust tier: agent data can never impersonate controller observations."""

    CONTROLLER_OBSERVED = "controller_observed"
    AGENT_REPORTED = "agent_reported"
    IMPORTED = "imported"


class Event(Contract):
    seq: NonNegativeInt
    episode_id: NonEmptyStr
    attempt_id: NonEmptyStr | None = None
    actor: NonEmptyStr
    kind: NonEmptyStr
    observation_source: ObservationSource
    causal_ids: list[NonEmptyStr] = Field(default_factory=list)
    payload: dict[str, Any] | None = None
    blob_refs: list[BlobRef] = Field(default_factory=list)


class FindingsSubmission(Contract):
    """The captured ``findings.json`` bytes, by digest (collect-then-match)."""

    kind: Literal["findings"] = "findings"
    sha256: Sha256Hex
    size_bytes: NonNegativeInt


class PocRefSubmission(Contract):
    """A PoC the agent submitted: stored as evidence, never executed in v0.1 (ADR-0004)."""

    kind: Literal["poc_ref"] = "poc_ref"
    sha256: Sha256Hex
    executed: Literal[False] = False


Submission = Annotated[FindingsSubmission | PocRefSubmission, Field(discriminator="kind")]
