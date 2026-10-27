# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Submission size limit (threat model T-DOS-1; scoring.md §3, §5.2)."""

from __future__ import annotations

from aureproof.scoring import V0_1, SubmissionStatus, parse_submission


def test_submission_at_the_byte_limit_is_parsed() -> None:
    data = b"[" + b" " * (V0_1.max_bytes - 2) + b"]"
    assert len(data) == V0_1.max_bytes
    assert parse_submission(data).status is SubmissionStatus.PARSED


def test_oversized_submission_is_rejected_before_decoding() -> None:
    data = b"[" + b" " * (V0_1.max_bytes - 1) + b"]"
    parsed = parse_submission(data)
    assert parsed.status is SubmissionStatus.MALFORMED
    assert parsed.reason == "larger than max_bytes"
