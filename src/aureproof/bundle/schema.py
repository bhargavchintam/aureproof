# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""JSON Schema 2020-12 for bundle records (no I/O; see scripts/export_schemas.py)."""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from aureproof.bundle.models import JournalEntry, Manifest, Statement

SCHEMA_DIR = "specs/bundle/v0.1"
DIALECT = "https://json-schema.org/draft/2020-12/schema"
_TARGETS: dict[str, Any] = {
    "manifest": Manifest,
    "seal-statement": Statement,
    "journal-entry": JournalEntry,
}


def export_schemas() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name, target in _TARGETS.items():
        schema = TypeAdapter(target).json_schema(mode="validation", by_alias=True)
        out[name] = {"$schema": DIALECT, "title": schema.pop("title", name), **schema}
    return out
