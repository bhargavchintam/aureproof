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
from aureproof.contracts.specs import (
    AgentView,
    AttemptRecord,
    Budget,
    EpisodeSpec,
    FileDigest,
    ModelBinding,
    ProviderIdentity,
    Runner,
    Subject,
    SystemSpec,
    TaskSpec,
    content_identity,
)
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
    "AgentView",
    "Anchor",
    "AttemptRecord",
    "Budget",
    "Defect",
    "Disposition",
    "EpisodeSignals",
    "EpisodeSpec",
    "Event",
    "FileDigest",
    "Finding",
    "FindingsSubmission",
    "FocalNegative",
    "LabelSet",
    "Location",
    "MatchInfo",
    "MetricRecord",
    "ModelBinding",
    "ObservationSource",
    "PocRefSubmission",
    "ProviderIdentity",
    "Role",
    "Rule",
    "Runner",
    "RunnerOutcome",
    "ScopeEntry",
    "Subject",
    "Submission",
    "SystemSpec",
    "TaskSpec",
    "VerdictKind",
    "VerdictRecord",
    "content_identity",
]
