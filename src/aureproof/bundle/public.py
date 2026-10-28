# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Public (redacted) bundles: redaction, secret scan, publication check (issue #46).

A public bundle is a distinct product from the private complete one (plan
v2 §4.2): it declares ``completeness: redacted``, carries no evaluator labels,
and must contain no credential-like strings. Redaction re-seals, so a public
bundle needs its own signature.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from aureproof.bundle.build import Member, build_bundle
from aureproof.bundle.models import BLOB_PREFIX, JOURNAL, MANIFEST, SEAL, Manifest
from aureproof.contracts.events import Event

SECRET_PATTERNS = {
    "anthropic_key": re.compile(rb"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "openai_key": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9]{20,}"),
    "aws_access_key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})"),
    "slack_token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----"),
}


def secret_findings(files: Mapping[str, bytes]) -> list[str]:
    """``path: kind`` for every credential-like string. Never prints the secret."""
    return [
        f"{path}: {kind}"
        for path, data in sorted(files.items())
        for kind, pattern in SECRET_PATTERNS.items()
        if pattern.search(data)
    ]


def public_problems(files: Mapping[str, bytes]) -> list[str]:
    """Why this bundle must not be published; empty means it may be."""
    problems: list[str] = []
    try:
        predicate = json.loads(files[SEAL])["predicate"]
        manifest = Manifest.model_validate_json(files[MANIFEST])
    except (KeyError, ValueError) as exc:
        return [f"unreadable seal or manifest: {exc}"]
    if predicate.get("completeness") != "redacted":
        problems.append("completeness is not 'redacted': this is a private, complete bundle")
    labels = [m.path for m in manifest.members if m.role == "labels"]
    if labels:
        problems.append("evaluator labels present: " + ", ".join(labels))
    problems += [f"secret-like string in {hit}" for hit in secret_findings(files)]
    return problems


def redact(files: Mapping[str, bytes]) -> dict[str, bytes]:
    """Re-seal without evaluator labels, as ``completeness: redacted``.

    Episode records still name their label paths, so a redacted bundle can be
    validated but not re-scored (``aureproof score --offline`` reports
    ``not_rescorable``), which is the point.
    """
    manifest = Manifest.model_validate_json(files[MANIFEST])
    predicate = json.loads(files[SEAL])["predicate"]
    members = [
        Member(m.path, files[m.path], m.role, m.media_type, m.mandatory)
        for m in manifest.members
        if m.role not in ("journal", "blob", "labels")
    ]
    events = [
        Event.model_validate(json.loads(line)["event"]) for line in files[JOURNAL].splitlines()
    ]
    blobs = [data for path, data in sorted(files.items()) if path.startswith(BLOB_PREFIX)]
    return build_bundle(
        members,
        events,
        blobs=blobs,
        versions=predicate["versions"],
        generator=predicate["generator"],
        completeness="redacted",
    )
