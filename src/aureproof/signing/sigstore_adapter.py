# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Sigstore adapter. Imports ``sigstore`` lazily (optional ``sign`` extra)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from aureproof.bundle.models import SEAL, SIGNATURE
from aureproof.bundle.validate import SignatureCheck

EXPECTED_IDENTITY = (
    "https://github.com/bhargavchintam/aureproof/.github/workflows/sign.yml@refs/heads/main"
)
EXPECTED_ISSUER = "https://token.actions.githubusercontent.com"


def signature_path(path: Path) -> Path:
    """``seal.sigstore.json`` inside a bundle directory; ``<file>.sigstore.json`` otherwise."""
    return path / SIGNATURE if path.is_dir() else path.with_name(path.name + ".sigstore.json")


def sign_bytes(data: bytes) -> str:
    """Keyless signature over exactly ``data`` with the ambient OIDC identity.

    In GitHub Actions this needs ``permissions: id-token: write``. Returns the
    Sigstore bundle JSON (certificate, signature, transparency-log entry).
    """
    from sigstore.models import ClientTrustConfig
    from sigstore.oidc import IdentityToken, detect_credential
    from sigstore.sign import SigningContext

    token = detect_credential()
    if token is None:
        raise RuntimeError("no ambient OIDC credential: run inside the sign.yml workflow")
    context = SigningContext.from_trust_config(ClientTrustConfig.production())
    with context.signer(IdentityToken(token), cache=False) as signer:
        bundle = signer.sign_artifact(data)
    signed: str = bundle.to_json()
    return signed


def verify_bytes(
    data: bytes,
    bundle_json: bytes | str,
    *,
    identity: str = EXPECTED_IDENTITY,
    issuer: str = EXPECTED_ISSUER,
) -> SignatureCheck:
    """Offline verification against the expected signer identity. Never raises."""
    from sigstore.errors import Error as SigstoreError
    from sigstore.models import Bundle
    from sigstore.verify import Verifier, policy

    try:
        bundle = Bundle.from_json(bundle_json)
        verifier = Verifier.production(offline=True)
        verifier.verify_artifact(data, bundle, policy.Identity(identity=identity, issuer=issuer))
    except (SigstoreError, ValueError, KeyError, TypeError) as exc:
        return SignatureCheck(
            verified=False,
            identity=identity,
            issuer=issuer,
            problems=(f"signature verification failed: {exc}",),
        )
    return SignatureCheck(verified=True, identity=identity, issuer=issuer)


def verify_bundle(
    files: Mapping[str, bytes],
    *,
    identity: str = EXPECTED_IDENTITY,
    issuer: str = EXPECTED_ISSUER,
) -> SignatureCheck:
    """Verify ``seal.sigstore.json`` over the exact ``seal.intoto.json`` bytes."""
    if SIGNATURE not in files:
        return SignatureCheck(
            verified=False,
            identity=identity,
            issuer=issuer,
            problems=("unsigned: no seal.sigstore.json",),
        )
    if SEAL not in files:
        return SignatureCheck(verified=False, problems=("no seal.intoto.json to verify",))
    return verify_bytes(files[SEAL], files[SIGNATURE], identity=identity, issuer=issuer)
