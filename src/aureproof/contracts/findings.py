# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Agent-authored findings (specs/scoring/scoring.md §2.1, §4.1).

Validation here covers the shape rules N1-N4 that need no context. Checks that
need the agent view (the file exists; lines are within the file) belong to the
matcher. A finding that fails either becomes an ``invalid`` verdict (M9); it
never raises past the matcher.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    Strict,
    WithJsonSchema,
    field_validator,
    model_validator,
)

from aureproof.contracts._base import NonEmptyStr, PositiveInt

MAX_LOCATIONS = 4  # scoring.md §3, fixed by matcher_version 0.1.0
MAX_DESCRIPTION = 4000
_CWE_STRING = re.compile(r"(?i)cwe-([0-9]+)")
# N1 syntax: relative, POSIX, no ".." segment (a leading "./" is allowed and stripped).
_PATH_PATTERN = r"^(?!/)(?!.*\\)(?!(.*/)?\.\.(/|$)).+$"


class Role(StrEnum):
    SITE = "site"
    SOURCE = "source"
    SINK = "sink"


def _coerce_cwe(value: Any) -> Any:
    """N3: "CWE-89", "cwe-89" and 89 are equal; anything else is left to fail."""
    if isinstance(value, str) and (m := _CWE_STRING.fullmatch(value)):
        return int(m.group(1))
    return value


Cwe = Annotated[
    PositiveInt,
    BeforeValidator(_coerce_cwe),
    WithJsonSchema(
        {
            "anyOf": [
                {"type": "integer", "minimum": 1},
                {"type": "string", "pattern": "^[Cc][Ww][Ee]-[0-9]+$"},
            ],
            "description": 'CWE ID: an integer, or a string such as "CWE-89" (N3).',
        }
    ),
]


class Location(BaseModel):
    """One place a finding points at. Lines are 1-based and inclusive."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        # N4 in the schema too; end_line >= start_line is enforced by the model only.
        json_schema_extra={"anyOf": [{"required": ["symbol"]}, {"required": ["start_line"]}]},
    )

    file: Annotated[str, Field(min_length=1, json_schema_extra={"pattern": _PATH_PATTERN})]
    symbol: NonEmptyStr | None = None
    start_line: PositiveInt | None = None
    end_line: PositiveInt | None = None
    role: Role = Role.SITE

    @field_validator("file")
    @classmethod
    def _workspace_relative(cls, value: str) -> str:  # N1 (syntax part)
        value = value.removeprefix("./")
        if not value or value.startswith("/") or "\\" in value or ".." in value.split("/"):
            raise ValueError("file must be a workspace-relative POSIX path")
        return value

    @model_validator(mode="after")
    def _lines(self) -> Self:  # N2, N4
        if self.symbol is None and self.start_line is None:
            raise ValueError("a location needs a symbol, a start_line, or both")
        if self.start_line is None:
            if self.end_line is not None:
                raise ValueError("end_line requires start_line")
            return self
        if self.end_line is None:
            return self.model_copy(update={"end_line": self.start_line})
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class Finding(BaseModel):
    """One reported defect. Unknown fields are kept as evidence, never matched."""

    model_config = ConfigDict(frozen=True, extra="allow")

    cwe: Cwe
    locations: Annotated[list[Location], Field(min_length=1, max_length=MAX_LOCATIONS)]
    description: Annotated[str, Strict(), Field(min_length=1, max_length=MAX_DESCRIPTION)]
    finding_id: NonEmptyStr | None = None
