# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Data contracts (pure core): findings, labels, verdicts, events.

Semantics are defined in ``specs/scoring/scoring.md``; JSON Schemas are exported
to ``specs/contracts/v0.1/`` by ``scripts/export_schemas.py``.
"""

from aureproof.contracts.events import (
    Event,
    FindingsSubmission,
    ObservationSource,
    PocRefSubmission,
    Submission,
)
from aureproof.contracts.findings import MAX_LOCATIONS, Finding, Location, Role
from aureproof.contracts.labels import Anchor, Defect, FocalNegative, LabelSet, ScopeEntry
from aureproof.contracts.verdicts import (
    Disposition,
    EpisodeSignals,
    MatchInfo,
    MetricRecord,
    Rule,
    RunnerOutcome,
    VerdictKind,
    VerdictRecord,
)

__all__ = [
    "MAX_LOCATIONS",
    "Anchor",
    "Defect",
    "Disposition",
    "EpisodeSignals",
    "Event",
    "Finding",
    "FindingsSubmission",
    "FocalNegative",
    "LabelSet",
    "Location",
    "MatchInfo",
    "MetricRecord",
    "ObservationSource",
    "PocRefSubmission",
    "Role",
    "Rule",
    "RunnerOutcome",
    "ScopeEntry",
    "Submission",
    "VerdictKind",
    "VerdictRecord",
]
