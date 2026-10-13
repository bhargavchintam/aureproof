# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Shared model configuration for the contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, Strict

Variant = Literal["vulnerable", "repaired"]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
BlobRef = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
NonEmptyStr = Annotated[str, Field(min_length=1)]
# Integers and booleans never accept strings, floats or bools-as-ints.
PositiveInt = Annotated[int, Strict(), Field(ge=1)]
NonNegativeInt = Annotated[int, Strict(), Field(ge=0)]
StrictBool = Annotated[bool, Strict()]


class Contract(BaseModel):
    """Evaluator-authored record: immutable, no unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")
