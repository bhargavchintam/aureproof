# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Evidence Bundle v0.1 (pure core): canonical digests, journal, seal, validation.

Normative definition: ``specs/bundle/README.md``. File I/O lives in the CLI.
"""

from aureproof.bundle.build import BundleError, Member, build_bundle
from aureproof.bundle.canonical import GENESIS, canonical_json, digest_ref, sha256_hex
from aureproof.bundle.models import BUNDLE_VERSION, PREDICATE_TYPE, Manifest, Statement
from aureproof.bundle.validate import Check, Report, validate

__all__ = [
    "BUNDLE_VERSION",
    "GENESIS",
    "PREDICATE_TYPE",
    "BundleError",
    "Check",
    "Manifest",
    "Member",
    "Report",
    "Statement",
    "build_bundle",
    "canonical_json",
    "digest_ref",
    "sha256_hex",
    "validate",
]
