# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Strict parsing of the captured submission bytes (scoring.md §5.2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from aureproof.contracts.strict_json import JsonInputError, loads_strict
from aureproof.scoring.params import V0_1, MatcherParams, matcher_version_of


class SubmissionStatus(StrEnum):
    ABSENT = "absent"
    MALFORMED = "malformed"
    PARSED = "parsed"


@dataclass(frozen=True, slots=True)
class ParsedSubmission:
    status: SubmissionStatus
    findings: tuple[Any, ...] = ()
    reason: str | None = None


def parse_submission(data: bytes | None, params: MatcherParams = V0_1) -> ParsedSubmission:
    """RFC 8259 JSON array, UTF-8, no duplicate keys or NaN/Infinity, within limits.

    Bounded: depth is checked before parsing, so hostile nesting cannot exhaust
    the interpreter stack (issue #35).
    """
    matcher_version_of(params)  # limits are part of the version (issue #36)
    if data is None:
        return ParsedSubmission(SubmissionStatus.ABSENT, reason="no submission captured")
    if len(data) > params.max_bytes:
        return ParsedSubmission(SubmissionStatus.MALFORMED, reason="larger than max_bytes")
    try:
        value = loads_strict(data, max_depth=params.max_depth)
    except JsonInputError as exc:
        return ParsedSubmission(SubmissionStatus.MALFORMED, reason=str(exc))
    if not isinstance(value, list):
        return ParsedSubmission(
            SubmissionStatus.MALFORMED, reason="top-level value is not an array"
        )
    if len(value) > params.max_findings:
        return ParsedSubmission(SubmissionStatus.MALFORMED, reason="more than max_findings")
    return ParsedSubmission(SubmissionStatus.PARSED, findings=tuple(value))
