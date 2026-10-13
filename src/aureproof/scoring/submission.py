# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Strict parsing of the captured submission bytes (scoring.md §5.2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from aureproof.scoring.params import V0_1, MatcherParams


class SubmissionStatus(StrEnum):
    ABSENT = "absent"
    MALFORMED = "malformed"
    PARSED = "parsed"


@dataclass(frozen=True, slots=True)
class ParsedSubmission:
    status: SubmissionStatus
    findings: tuple[Any, ...] = ()
    reason: str | None = None


class _Malformed(ValueError):
    pass


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise _Malformed("duplicate object key")
    return dict(pairs)


def _no_constants(token: str) -> Any:
    raise _Malformed(f"non-standard JSON value {token}")


def parse_submission(data: bytes | None, params: MatcherParams = V0_1) -> ParsedSubmission:
    """RFC 8259 JSON array, UTF-8, no duplicate keys or NaN/Infinity, within limits."""
    if data is None:
        return ParsedSubmission(SubmissionStatus.ABSENT, reason="no submission captured")
    if len(data) > params.max_bytes:
        return ParsedSubmission(SubmissionStatus.MALFORMED, reason="larger than max_bytes")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_no_constants,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        return ParsedSubmission(SubmissionStatus.MALFORMED, reason=str(exc) or type(exc).__name__)
    if not isinstance(value, list):
        return ParsedSubmission(
            SubmissionStatus.MALFORMED, reason="top-level value is not an array"
        )
    if len(value) > params.max_findings:
        return ParsedSubmission(SubmissionStatus.MALFORMED, reason="more than max_findings")
    return ParsedSubmission(SubmissionStatus.PARSED, findings=tuple(value))
