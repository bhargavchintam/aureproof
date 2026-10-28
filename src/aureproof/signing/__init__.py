# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Sigstore signing and offline verification (adapter; ``sign`` extra; issue #46).

Signer identity policy (decided 2026-10-28): evidence is signed **only** by this
repository's GitHub Actions workflow ``.github/workflows/sign.yml`` running on
``main``, with GitHub's OIDC issuer. Keyless: no long-lived signing key exists.

Verification is offline. It uses the trust root shipped in the pinned
``sigstore`` package (never one supplied by the bundle being checked) and the
certificate, signature and transparency-log inclusion proof carried in the
signature bundle.
"""

from aureproof.signing.sigstore_adapter import (
    EXPECTED_IDENTITY,
    EXPECTED_ISSUER,
    sign_bytes,
    signature_path,
    verify_bundle,
    verify_bytes,
)

__all__ = [
    "EXPECTED_IDENTITY",
    "EXPECTED_ISSUER",
    "sign_bytes",
    "signature_path",
    "verify_bundle",
    "verify_bytes",
]
