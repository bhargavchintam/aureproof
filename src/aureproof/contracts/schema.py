# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""JSON Schema 2020-12 export for the contracts (no I/O; see scripts/export_schemas.py)."""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from aureproof.contracts.events import Event, Submission
from aureproof.contracts.findings import Finding
from aureproof.contracts.labels import LabelSet
from aureproof.contracts.specs import AttemptRecord, EpisodeSpec, SystemSpec, TaskSpec
from aureproof.contracts.verdicts import EpisodeSignals, MetricRecord, VerdictRecord

SCHEMA_DIR = "specs/contracts/v0.1"
DIALECT = "https://json-schema.org/draft/2020-12/schema"

_TARGETS: dict[str, Any] = {
    "finding": Finding,
    "findings-file": list[Finding],
    "label-set": LabelSet,
    "verdict-record": VerdictRecord,
    "episode-signals": EpisodeSignals,
    "metric-record": MetricRecord,
    "event": Event,
    "submission": Submission,
    "task-spec": TaskSpec,
    "system-spec": SystemSpec,
    "episode-spec": EpisodeSpec,
    "attempt-record": AttemptRecord,
}


def export_schemas() -> dict[str, dict[str, Any]]:
    """Validation-mode schemas keyed by file stem (``<stem>.schema.json``)."""
    out: dict[str, dict[str, Any]] = {}
    for name, target in _TARGETS.items():
        schema = TypeAdapter(target).json_schema(mode="validation")
        out[name] = {"$schema": DIALECT, "title": schema.pop("title", name), **schema}
    return out
