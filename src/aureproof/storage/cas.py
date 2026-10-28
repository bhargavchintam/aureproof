# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Content-addressed blob store on disk: ``<root>/sha256/<hex>`` (issue #16)."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from aureproof.bundle.canonical import sha256_hex
from aureproof.storage.fs import StorageError

_REF = "sha256:"


class BlobStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, ref: str) -> Path:
        hexdigest = ref.removeprefix(_REF)
        if (
            not ref.startswith(_REF)
            or len(hexdigest) != 64
            or not all(c in "0123456789abcdef" for c in hexdigest)
        ):
            raise StorageError(f"not a sha256 reference: {ref!r}")
        return self.root / "sha256" / hexdigest

    def put(self, data: bytes) -> str:
        ref = _REF + sha256_hex(data)
        path = self._path(ref)
        if path.is_symlink():
            raise StorageError(f"symlink rejected: {path}")
        if path.exists():
            if self.get(ref) != data:  # pragma: no cover - get() already verifies
                raise StorageError(f"corrupt blob {ref}")
            return ref
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".{path.name}.tmp-{secrets.token_hex(8)}"
        with tmp.open("xb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(path)  # atomic; identical content if two writers race
        return ref

    def get(self, ref: str) -> bytes:
        path = self._path(ref)
        if path.is_symlink():
            raise StorageError(f"symlink rejected: {path}")
        data = path.read_bytes()
        if _REF + sha256_hex(data) != ref:
            raise StorageError(f"blob {ref} does not match its content")
        return data
