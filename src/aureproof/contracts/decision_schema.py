# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""JSON Schema 2020-12 for the Decision Protocol and Decision (see scripts/export_schemas.py)."""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from aureproof.contracts.decision import Decision, DecisionProtocol

SCHEMA_DIR = "specs/decision/v0.1"
DIALECT = "https://json-schema.org/draft/2020-12/schema"


def export_schemas() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name, target in (("protocol", DecisionProtocol), ("decision", Decision)):
        schema = TypeAdapter(target).json_schema(mode="validation")
        out[name] = {"$schema": DIALECT, "title": schema.pop("title", name), **schema}
    return out
