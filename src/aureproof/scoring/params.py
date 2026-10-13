# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Versions and parameters of scoring/v0.1 (specs/scoring/scoring.md §3)."""

from __future__ import annotations

from dataclasses import dataclass

from aureproof.contracts.findings import MAX_LOCATIONS

MATCHER_VERSION = "0.1.0"
DISPOSITION_VERSION = "0.1.0"
METRICS_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class MatcherParams:
    """Fixed by ``matcher_version``: changing any value is a new version."""

    line_tolerance: int = 3
    max_line_span: int = 30
    max_locations: int = MAX_LOCATIONS
    max_findings: int = 256
    max_bytes: int = 1_048_576


V0_1 = MatcherParams()
