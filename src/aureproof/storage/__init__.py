# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Filesystem adapters (not pure core): bundle directories and a content-addressed store."""

from aureproof.storage.cas import BlobStore
from aureproof.storage.fs import MAX_BUNDLE_BYTES, StorageError, read_bundle, write_bundle

__all__ = ["MAX_BUNDLE_BYTES", "BlobStore", "StorageError", "read_bundle", "write_bundle"]
