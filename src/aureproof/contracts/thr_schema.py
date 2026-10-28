# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""JSON Schema 2020-12 for the Task Health Record (see scripts/export_schemas.py)."""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from aureproof.contracts.thr import TaskHealthRecord

SCHEMA_DIR = "specs/thr/v0.1"
DIALECT = "https://json-schema.org/draft/2020-12/schema"


def export_schemas() -> dict[str, dict[str, Any]]:
    schema = TypeAdapter(TaskHealthRecord).json_schema(mode="validation")
    return {"thr": {"$schema": DIALECT, "title": schema.pop("title", "thr"), **schema}}
