# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Validate a bundle offline (bundle spec §7). Reports every failed check."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import ValidationError

from aureproof.bundle.build import entry_hash, valid_path
from aureproof.bundle.canonical import (
    GENESIS,
    NotCanonicalizable,
    canonical_json,
    digest_ref,
    sha256_hex,
)
from aureproof.bundle.models import (
    BLOB_PREFIX,
    JOURNAL,
    MANDATORY_ROLES,
    MANIFEST,
    RESERVED,
    SEAL,
    SIGNATURE,
    JournalEntry,
    Manifest,
    Statement,
)
from aureproof.contracts.events import Event
from aureproof.contracts.strict_json import JsonInputError, loads_strict

CheckId = Literal["V1", "V2", "V3", "V4", "V5", "V6"]
NAMES: dict[str, str] = {
    "V1": "structure",
    "V2": "members",
    "V3": "journal",
    "V4": "mandatory evidence",
    "V5": "signature",
    "V6": "identity",
}


@dataclass
class Check:
    id: str
    status: Literal["pass", "fail", "skipped"] = "pass"
    problems: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return NAMES[self.id]

    def fail(self, problem: str) -> None:
        self.status = "fail"
        self.problems.append(problem)


@dataclass(frozen=True)
class SignatureCheck:
    """The result of verifying ``seal.sigstore.json``, computed by a signing adapter.

    The pure core cannot verify signatures (no crypto, no trust root); an adapter
    such as ``aureproof.signing`` does, and hands the result to ``validate``.
    """

    verified: bool
    identity: str | None = None
    issuer: str | None = None
    problems: tuple[str, ...] = ()


@dataclass
class Report:
    checks: list[Check]

    @property
    def valid(self) -> bool:
        return all(c.status != "fail" for c in self.checks)

    @property
    def signed(self) -> bool:
        """True only when a signature was verified (V5 pass). Distinct from validity."""
        return any(c.id == "V5" and c.status == "pass" for c in self.checks)

    def problems(self) -> list[str]:
        return [f"{c.id} {c.name}: {p}" for c in self.checks for p in c.problems]


def _canonical_doc(data: bytes, what: str, check: Check) -> Any:
    """Parse strictly (bounded, I-JSON) and require RFC 8785 bytes. Never raises."""
    try:
        value = loads_strict(data, i_json=True)
    except JsonInputError as exc:
        check.fail(f"{what} is not acceptable JSON: {exc}")
        return None
    try:
        canonical = canonical_json(value)
    except NotCanonicalizable as exc:  # pragma: no cover - loads_strict(i_json) prevents it
        check.fail(f"{what} has no RFC 8785 form: {exc}")
        return None
    if canonical != data:
        check.fail(f"{what} is not in RFC 8785 canonical form")
    return value


def validate(
    files: Mapping[str, bytes],
    *,
    trusted_seal_digest: str | None = None,
    signature: SignatureCheck | None = None,
) -> Report:
    """Run V1-V6. ``trusted_seal_digest`` (``sha256:<hex>`` of ``seal.intoto.json``,
    recorded out of band) is the trust root for an unsigned bundle: without it, the
    seal's own metadata cannot be authenticated (spec §1)."""
    v1, v2, v3, v4, v5, v6 = (Check(i) for i in ("V1", "V2", "V3", "V4", "V5", "V6"))
    if signature is None:
        v5.status = "skipped"
        v5.problems.append(
            "signature present but not verified"
            if SIGNATURE in files
            else "unsigned: no seal.sigstore.json"
        )
    elif signature.verified:
        v5.problems.append(f"verified: {signature.identity} (issuer {signature.issuer})")
    else:
        v5.status = "fail"
        v5.problems.extend(signature.problems or ("signature verification failed",))
    report = Report([v1, v2, v3, v4, v5, v6])

    # V1 structure
    for path in files:
        if not valid_path(path):
            v1.fail(f"invalid path {path!r}")
    for required in (MANIFEST, SEAL, JOURNAL):
        if required not in files:
            v1.fail(f"{required} is missing")
    manifest: Manifest | None = None
    statement: Statement | None = None
    if MANIFEST in files:
        raw = _canonical_doc(files[MANIFEST], MANIFEST, v1)
        if raw is not None:
            try:
                manifest = Manifest.model_validate(raw)
            except ValidationError as exc:
                v1.fail(f"{MANIFEST} does not match the schema: {exc.error_count()} errors")
    if SEAL in files:
        raw = _canonical_doc(files[SEAL], SEAL, v1)
        if raw is not None:
            try:
                statement = Statement.model_validate(raw)
            except ValidationError as exc:
                v1.fail(f"{SEAL} does not match the schema: {exc.error_count()} errors")
    if manifest is not None:
        paths = [m.path for m in manifest.members]
        if paths != sorted(set(paths), key=str.encode):
            v1.fail("manifest members are not sorted by path or contain duplicates")

    # V2 members
    listed = {m.path: m for m in manifest.members} if manifest else {}
    for path, member in listed.items():
        if path not in files:
            v2.fail(f"{path} is listed but missing")
            continue
        data = files[path]
        if len(data) != member.size or sha256_hex(data) != member.sha256:
            v2.fail(f"{path} does not match its manifest digest or size")
    if manifest is not None:
        for path in sorted(set(files) - set(listed) - RESERVED):
            v2.fail(f"{path} is not listed in the manifest")
    for path, data in files.items():
        if path.startswith(BLOB_PREFIX) and path.removeprefix(BLOB_PREFIX) != sha256_hex(data):
            v2.fail(f"{path} is not named by its own digest")

    # V3 journal
    count, head = 0, GENESIS
    seq_ok = True
    if JOURNAL in files:
        data = files[JOURNAL]
        if data and not data.endswith(b"\n"):
            v3.fail("journal does not end with a newline")
        lines = data.split(b"\n")[:-1] if data else []
        prev = GENESIS
        for index, line in enumerate(lines):
            raw = _canonical_doc(line, f"journal line {index}", v3)
            try:
                entry = JournalEntry.model_validate(raw)
            except ValidationError:
                v3.fail(f"journal line {index} is not a valid entry")
                seq_ok = False
                break
            try:
                event: Event | None = Event.model_validate(entry.event)
            except ValidationError:
                v3.fail(f"journal line {index} carries an invalid event")
                event = None
            if entry.seq != index or (event is not None and event.seq != index):
                v3.fail(f"journal line {index} has seq {entry.seq}, expected {index}")
            if entry.prev != prev:
                v3.fail(f"journal line {index} does not link to the previous entry")
            try:  # hash exactly the recorded event, not a re-serialized model
                recomputed = entry_hash(entry.seq, entry.prev, entry.event)
            except NotCanonicalizable:
                recomputed = None
            if entry.hash != recomputed:
                v3.fail(f"journal line {index} hash does not recompute")
            prev = entry.hash
            count += 1
            for ref in event.blob_refs if event is not None else ():
                if BLOB_PREFIX + ref.removeprefix("sha256:") not in files:
                    v6.fail(f"journal line {index} references a missing blob {ref}")
        head = prev
    if statement is not None and seq_ok:
        if statement.predicate.event_count != count:
            v3.fail(f"seal records {statement.predicate.event_count} events, journal has {count}")
        if statement.predicate.journal_head != head:
            v3.fail("journal head does not match the seal")

    # V4 mandatory evidence
    if manifest is not None:
        for role in MANDATORY_ROLES:
            holders = [m for m in manifest.members if m.role == role]
            if len(holders) != 1 or not holders[0].mandatory:
                v4.fail(f"mandatory role {role!r} must appear exactly once, flagged mandatory")
        for member in manifest.members:
            if member.mandatory and member.path not in files:
                v4.fail(f"mandatory member {member.path} is absent")

    # V6 identity
    if trusted_seal_digest is not None and (
        SEAL not in files or digest_ref(files[SEAL]) != trusted_seal_digest
    ):
        v6.fail("seal digest differs from the trusted seal digest")
    if statement is not None:
        expected = sha256_hex(files[MANIFEST]) if MANIFEST in files else None
        subjects = [(s.name, s.digest.sha256) for s in statement.subject]
        if subjects != [(MANIFEST, expected)]:
            v6.fail("seal subject is not the manifest's digest")
        if manifest is not None and statement.predicate.bundle_version != manifest.bundle_version:
            v6.fail("seal and manifest disagree on bundle_version")
    return report
