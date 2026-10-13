# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Scoring (pure core): the v0.1 label matcher, dispositions and metrics.

Normative definition: ``specs/scoring/scoring.md``. Golden vectors:
``conformance/scoring/v0.1/golden.json``.
"""

from aureproof.scoring.episode import GRADED, EpisodeScore, score_episode
from aureproof.scoring.matcher import MatchResult, match
from aureproof.scoring.metrics import compute_metrics
from aureproof.scoring.params import (
    DISPOSITION_VERSION,
    MATCHER_VERSION,
    METRICS_VERSION,
    V0_1,
    MatcherParams,
)
from aureproof.scoring.submission import ParsedSubmission, SubmissionStatus, parse_submission

__all__ = [
    "DISPOSITION_VERSION",
    "GRADED",
    "MATCHER_VERSION",
    "METRICS_VERSION",
    "V0_1",
    "EpisodeScore",
    "MatchResult",
    "MatcherParams",
    "ParsedSubmission",
    "SubmissionStatus",
    "compute_metrics",
    "match",
    "parse_submission",
    "score_episode",
]
