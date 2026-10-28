# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Manifest, journal entry and seal records (bundle spec §4-§6)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from aureproof.contracts._base import Contract, NonEmptyStr, NonNegativeInt, Sha256Hex

BUNDLE_VERSION = "0.1"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = (
    "https://github.com/bhargavchintam/aureproof/blob/main/specs/bundle/README.md#predicate-v01"
)
MANIFEST = "manifest.json"
SEAL = "seal.intoto.json"
JOURNAL = "journal.jsonl"
SIGNATURE = "seal.sigstore.json"
RESERVED = frozenset({MANIFEST, SEAL, SIGNATURE})
BLOB_PREFIX = "blobs/sha256/"
Role = Literal[
    "journal",
    "verdicts",
    "metrics",
    "adjudications",
    "protocol",
    "system",
    "task_health",
    "submission",
    "decision",
    "episodes",
    "labels",
    "blob",
    "other",
]
MANDATORY_ROLES: tuple[Role, ...] = ("journal", "verdicts", "metrics")
DigestRef = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class ManifestMember(Contract):
    path: NonEmptyStr
    sha256: Sha256Hex
    size: NonNegativeInt
    media_type: NonEmptyStr
    role: Role
    mandatory: bool


class Manifest(Contract):
    bundle_version: Literal["0.1"]
    members: list[ManifestMember]


class JournalEntry(Contract):
    """One journal line. ``event`` stays raw: V3 hashes exactly what was recorded and
    validates its shape against ``Event`` separately (issue #35)."""

    seq: NonNegativeInt
    prev: DigestRef
    event: dict[str, Any]
    hash: DigestRef


class Generator(Contract):
    name: NonEmptyStr
    version: NonEmptyStr


class Predicate(Contract):
    bundle_version: Literal["0.1"]
    event_count: NonNegativeInt
    journal_head: DigestRef
    completeness: Literal["complete", "redacted"]
    versions: dict[str, NonEmptyStr]
    generator: Generator


class SubjectDigest(Contract):
    sha256: Sha256Hex


class Subject(Contract):
    name: NonEmptyStr
    digest: SubjectDigest


class Statement(BaseModel):
    """in-toto Statement v1 (https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md)."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    type_: Literal["https://in-toto.io/Statement/v1"] = Field(alias="_type")
    subject: Annotated[list[Subject], Field(min_length=1)]
    predicateType: Literal[  # field name fixed by the in-toto spec
        "https://github.com/bhargavchintam/aureproof/blob/main/specs/bundle/README.md#predicate-v01"
    ]
    predicate: Predicate
