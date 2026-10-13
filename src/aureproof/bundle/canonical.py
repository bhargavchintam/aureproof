# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""RFC 8785 canonical JSON and SHA-256 digest references (bundle spec §2)."""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785

GENESIS = "sha256:" + "0" * 64


def canonical_json(value: Any) -> bytes:
    """The single valid byte form of a JSON value (RFC 8785 / JCS)."""
    return rfc8785.dumps(value)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_ref(value: bytes | Any) -> str:
    """``sha256:<hex>`` of raw bytes, or of a JSON value's canonical bytes."""
    data = value if isinstance(value, bytes) else canonical_json(value)
    return f"sha256:{sha256_hex(data)}"
