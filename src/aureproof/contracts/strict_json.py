# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Bounded, strict parsing for untrusted JSON (issue #35).

Every agent-controlled or bundle-supplied JSON document goes through
``loads_strict``. It never raises anything but ``JsonInputError``, and its
cost is linear in the input size: the nesting depth is checked by a single
scan *before* the recursive parser runs.
"""

from __future__ import annotations

import json
from typing import Any

MAX_JSON_DEPTH = 32
MAX_SAFE_INTEGER = 2**53 - 1  # I-JSON (RFC 7493) / RFC 8785 safe integer range


class JsonInputError(ValueError):
    """The bytes are not acceptable JSON; the message says why."""


def nesting_depth(text: str) -> int:
    """Maximum ``[``/``{`` nesting depth, ignoring brackets inside strings. O(n)."""
    depth = deepest = 0
    in_string = escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            deepest = max(deepest, depth)
        elif ch in "]}":
            depth -= 1
    return deepest


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({k for k, _ in pairs}) != len(pairs):
        raise JsonInputError("duplicate object key")
    return dict(pairs)


def _no_constants(token: str) -> Any:
    raise JsonInputError(f"non-standard JSON value {token}")


def _i_json_int(token: str) -> int | float:
    """JSON numbers are IEEE doubles (RFC 8785 §3.2.2.3; ECMAScript parsing): an
    integer token beyond the safe range denotes the nearest double. A token that is
    not that double's canonical text then fails the canonical-bytes comparison."""
    value = int(token)
    return value if abs(value) <= MAX_SAFE_INTEGER else float(value)


def check_i_json(value: Any) -> None:
    """Raise ``JsonInputError`` unless RFC 8785 can canonicalize ``value``."""
    _check_i_json(value)


def _check_i_json(value: Any, depth: int = 0) -> None:
    """Values RFC 8785 can canonicalize: safe integers, finite numbers, valid Unicode."""
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise JsonInputError("integer outside the I-JSON safe range")
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise JsonInputError("non-finite number")
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise JsonInputError("string contains a lone surrogate") from exc
    elif isinstance(value, list):
        for item in value:
            _check_i_json(item, depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_i_json(key, depth + 1)
            _check_i_json(item, depth + 1)


def loads_strict(data: bytes, *, max_depth: int = MAX_JSON_DEPTH, i_json: bool = False) -> Any:
    """RFC 8259 JSON from UTF-8 bytes: no duplicate keys, no NaN/Infinity, bounded depth.

    With ``i_json=True`` the value must also be representable in RFC 8785.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JsonInputError("not valid UTF-8") from exc
    if nesting_depth(text) > max_depth:
        raise JsonInputError(f"nested deeper than {max_depth}")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_no_constants,
            parse_int=_i_json_int if i_json else int,
        )
    except JsonInputError:
        raise
    except (ValueError, RecursionError) as exc:
        raise JsonInputError(str(exc) or type(exc).__name__) from exc
    if i_json:
        _check_i_json(value)
    return value
