# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Bounded, strict parsing of untrusted JSON (issue #35)."""

from __future__ import annotations

import contextlib
import time

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aureproof.contracts.strict_json import (
    MAX_JSON_DEPTH,
    JsonInputError,
    loads_strict,
    nesting_depth,
)
from aureproof.scoring import SubmissionStatus, parse_submission


def test_depth_scan_ignores_brackets_inside_strings() -> None:
    assert nesting_depth('[{"a": "[[[[{{{{\\"]]"}]') == 2
    assert nesting_depth('"[[["') == 0


def test_audit_case_deep_submission_below_byte_limit_is_rejected_quickly() -> None:
    """The audit's 20,001-byte, depth-10,000 submission raised RecursionError."""
    deep = b"[" * 10_000 + b"]" * 10_000 + b"\n"
    assert len(deep) == 20_001
    parsed = parse_submission(deep)
    assert parsed.status is SubmissionStatus.MALFORMED
    assert parsed.reason is not None and "deeper" in parsed.reason


def test_rejection_cost_is_linear() -> None:
    hostile = b"[" * 1_000_000  # 1 MB, the submission limit
    start = time.perf_counter()
    with pytest.raises(JsonInputError):
        loads_strict(hostile)
    assert time.perf_counter() - start < 2.0


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b'{"a": 1, "a": 2}', "duplicate"),
        (b"[NaN]", "NaN"),
        (b"[Infinity]", "Infinity"),
        (b"\xff[]", "UTF-8"),
        (b"[1,", ""),
        (b"[" * (MAX_JSON_DEPTH + 1) + b"]" * (MAX_JSON_DEPTH + 1), "deeper"),
    ],
)
def test_rejections_are_json_input_errors(data: bytes, reason: str) -> None:
    with pytest.raises(JsonInputError, match=reason):
        loads_strict(data)


@pytest.mark.parametrize(
    "data",
    [b'["\\ud800"]', b'{"\\udc00": 1}', b"[1e400]"],
)
def test_i_json_rejects_values_rfc8785_cannot_represent(data: bytes) -> None:
    loads_strict(data)  # acceptable RFC 8259 JSON ...
    with pytest.raises(JsonInputError):
        loads_strict(data, i_json=True)  # ... but not canonicalizable


def test_exact_depth_limit_is_accepted() -> None:
    assert loads_strict(b"[" * MAX_JSON_DEPTH + b"]" * MAX_JSON_DEPTH) is not None


@given(st.binary(max_size=300))
def test_never_raises_anything_but_json_input_error(data: bytes) -> None:
    with contextlib.suppress(JsonInputError):
        loads_strict(data, i_json=True)


def test_exactly_representable_large_integers_parse_as_doubles() -> None:
    """RFC 8785 numbers are doubles: 2**53 canonicalizes as an integer and must parse back."""
    assert loads_strict(b"[9007199254740992]", i_json=True) == [9007199254740992.0]
    assert loads_strict(b"[9007199254740992]") == [9007199254740992]
    # The nearest double to 2**53 + 1 is 2**53: accepted, but its canonical text differs,
    # so a bundle document containing it fails the RFC 8785 byte comparison.
    from aureproof.bundle import canonical_json

    value = loads_strict(b"[9007199254740993]", i_json=True)
    assert canonical_json(value) == b"[9007199254740992]"
