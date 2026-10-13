# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Seal a bundle (bundle spec §3-§6). Pure: files in, files out, no clock."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from aureproof.bundle.canonical import GENESIS, canonical_json, digest_ref, sha256_hex
from aureproof.bundle.models import (
    BLOB_PREFIX,
    BUNDLE_VERSION,
    JOURNAL,
    MANDATORY_ROLES,
    MANIFEST,
    PREDICATE_TYPE,
    RESERVED,
    SEAL,
    STATEMENT_TYPE,
    Role,
)
from aureproof.contracts.events import Event


class BundleError(ValueError):
    """The inputs cannot be sealed (for example, mandatory evidence is missing)."""


@dataclass(frozen=True, slots=True)
class Member:
    path: str
    data: bytes
    role: Role
    media_type: str = "application/json"
    mandatory: bool | None = None  # None: mandatory exactly when the role is


def valid_path(path: str) -> bool:
    """Relative POSIX path with no '.', '..' or empty segment (spec §3)."""
    return (
        bool(path)
        and not path.startswith("/")
        and "\\" not in path
        and all(seg not in ("", ".", "..") for seg in path.split("/"))
    )


def entry_hash(seq: int, prev: str, event: Mapping[str, object]) -> str:
    return digest_ref({"seq": seq, "prev": prev, "event": event})


def journal_bytes(events: Sequence[Event]) -> tuple[bytes, str]:
    """JSONL of chained entries, and the journal head."""
    lines: list[bytes] = []
    prev = GENESIS
    for seq, event in enumerate(events):
        if event.seq != seq:
            raise BundleError(f"event seq {event.seq} at position {seq}: seq must be 0, 1, 2, ...")
        body = event.model_dump(mode="json", exclude_none=True)
        current = entry_hash(seq, prev, body)
        lines.append(canonical_json({"seq": seq, "prev": prev, "event": body, "hash": current}))
        prev = current
    return b"".join(line + b"\n" for line in lines), prev


def build_bundle(
    members: Iterable[Member],
    events: Sequence[Event],
    *,
    blobs: Iterable[bytes],
    versions: Mapping[str, str],
    generator: Mapping[str, str],
    completeness: Literal["complete", "redacted"] = "complete",
) -> dict[str, bytes]:
    """Every bundle file, keyed by path. Refuses to seal incomplete evidence."""
    journal, head = journal_bytes(events)
    entries: dict[str, Member] = {JOURNAL: Member(JOURNAL, journal, "journal", "application/jsonl")}
    for blob in blobs:
        path = BLOB_PREFIX + sha256_hex(blob)
        entries[path] = Member(path, blob, "blob", "application/octet-stream")
    for member in members:
        if member.path in RESERVED or member.path == JOURNAL or member.path.startswith(BLOB_PREFIX):
            raise BundleError(f"{member.path} is a reserved path")
        if not valid_path(member.path):
            raise BundleError(f"invalid member path {member.path!r}")
        if member.path in entries:
            raise BundleError(f"duplicate member path {member.path}")
        entries[member.path] = member

    roles = [m.role for m in entries.values()]
    for role in MANDATORY_ROLES:
        if roles.count(role) != 1:
            raise BundleError(f"mandatory evidence missing or duplicated: role {role!r}")
    for event in events:
        for ref in event.blob_refs:
            if BLOB_PREFIX + ref.removeprefix("sha256:") not in entries:
                raise BundleError(f"event {event.seq} references a blob not in the bundle: {ref}")

    manifest = {
        "bundle_version": BUNDLE_VERSION,
        "members": [
            {
                "path": m.path,
                "sha256": sha256_hex(m.data),
                "size": len(m.data),
                "media_type": m.media_type,
                "role": m.role,
                "mandatory": m.role in MANDATORY_ROLES if m.mandatory is None else m.mandatory,
            }
            for m in sorted(entries.values(), key=lambda m: m.path.encode())
        ],
    }
    manifest_bytes = canonical_json(manifest)
    seal = {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": MANIFEST, "digest": {"sha256": sha256_hex(manifest_bytes)}}],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "bundle_version": BUNDLE_VERSION,
            "event_count": len(events),
            "journal_head": head,
            "completeness": completeness,
            "versions": dict(versions),
            "generator": dict(generator),
        },
    }
    files = {m.path: m.data for m in entries.values()}
    files[MANIFEST] = manifest_bytes
    files[SEAL] = canonical_json(seal)
    return files
