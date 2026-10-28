# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Versions, registered parameter profiles and the scoring identity (scoring.md §3).

A matcher version fixes every scoring parameter. Parameters that are not a
registered profile are rejected, so a verdict can never carry a version whose
semantics it did not use (issue #36).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from aureproof.contracts.canonical import digest_ref
from aureproof.contracts.findings import MAX_LOCATIONS
from aureproof.contracts.strict_json import MAX_JSON_DEPTH

MATCHER_VERSION = "0.1.0"
DISPOSITION_VERSION = "0.1.0"
METRICS_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class MatcherParams:
    """Fixed by ``matcher_version``. A different value is a different version."""

    line_tolerance: int = 3
    max_line_span: int = 30
    max_locations: int = MAX_LOCATIONS
    max_findings: int = 256
    max_bytes: int = 1_048_576
    max_depth: int = MAX_JSON_DEPTH


# matcher_version -> the only parameters that version may run with.
PROFILES: dict[str, MatcherParams] = {MATCHER_VERSION: MatcherParams()}
V0_1 = PROFILES[MATCHER_VERSION]


class UnregisteredParams(ValueError):
    """Parameters that no matcher version defines; refusing to score with them."""


def matcher_version_of(params: MatcherParams) -> str:
    for version, registered in PROFILES.items():
        if params == registered:
            return version
    raise UnregisteredParams(
        f"{params} is not a registered profile; a parameter change needs a new matcher_version"
    )


def scoring_identity(params: MatcherParams = V0_1) -> str:
    """``sha256:`` digest of every version and parameter that decides a verdict or metric.

    Saved and sealed records carry it, so an offline re-score can prove it used the
    same semantics.
    """
    return digest_ref(
        {
            "matcher_version": matcher_version_of(params),
            "disposition_version": DISPOSITION_VERSION,
            "metrics_version": METRICS_VERSION,
            "params": asdict(params),
        }
    )
