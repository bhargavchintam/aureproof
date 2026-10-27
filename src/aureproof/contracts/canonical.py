# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""RFC 8785 canonical JSON and SHA-256 digest references.

Shared by content identities (task, system, episode) and the Evidence Bundle
(specs/bundle §2). Lives in the contracts layer so both can use it.
"""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785

GENESIS = "sha256:" + "0" * 64


class NotCanonicalizable(ValueError):
    """The value has no RFC 8785 form (NaN, unsafe integer, lone surrogate, ...)."""


def canonical_json(value: Any) -> bytes:
    """The single valid byte form of a JSON value (RFC 8785 / JCS)."""
    try:
        return rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, TypeError, ValueError) as exc:
        raise NotCanonicalizable(str(exc)) from exc


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_ref(value: bytes | Any) -> str:
    """``sha256:<hex>`` of raw bytes, or of a JSON value's canonical bytes."""
    data = value if isinstance(value, bytes) else canonical_json(value)
    return f"sha256:{sha256_hex(data)}"
