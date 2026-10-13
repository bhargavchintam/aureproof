<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Evidence Bundle specification

- Spec: `bundle/v0.1`. Status: **draft, pending a second review** (issue #13, AP-036; ADR-0005).
- Normative source: [`docs/aureproof-plan-v2.md`](../../docs/aureproof-plan-v2.md) §3.5 and §4.2. This document refines them; where they differ, this document wins.
- Reference implementation: `aureproof.bundle` (pure; no file or network I/O). Conformance vectors: [`conformance/bundle/v0.1/`](../../conformance/bundle/v0.1/).
- Signing with Sigstore is M2. A v0.1 bundle is **sealed** (integrity and completeness) but may be **unsigned** (no identity).

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Purpose

A bundle is a self-contained, offline-verifiable record of an evaluation. A third party can check, without network access and without re-running any model:

1. every recorded byte is the byte that was sealed;
2. no journal event was removed, reordered or appended after sealing;
3. every mandatory piece of evidence is present.

They can then re-score it offline. **A hash proves the integrity of recorded bytes, not that the recorded claim is true.**

**What sealing does not do.** An unsigned seal proves integrity only *relative to a seal digest you already trust*. Anyone who can rewrite every file can produce a different, internally consistent bundle. Integrity becomes attributable only when one of these holds:

- the seal is signed (Sigstore, M2);
- the seal's digest is recorded somewhere the producer can't later change, such as a PR comment, a release note or a transparency log.

Validators report V5 (signature) as `skipped`, never as a pass. A validator SHOULD accept a *trusted seal digest*, the digest of `seal.intoto.json` recorded out-of-band, and fail V6 when it differs. Only then does every byte of an unsigned bundle become tamper-evident, including the seal's own metadata (`generator`, `versions`, `completeness`).

## 2. Canonical form and digests

- **Canonical JSON** is RFC 8785 (JCS). Every JSON document defined here is stored as exactly its JCS bytes, so a document has a single valid byte sequence. Validation rejects non-canonical bytes.
- **Digests** are SHA-256, written as lowercase hex. A *digest reference* is `sha256:<64 hex>`.
- **The digest of a JSON value** is the SHA-256 of its JCS bytes.

## 3. Layout

A bundle is a set of files keyed by path. Paths are workspace-style:
- relative POSIX;
- no leading `/`, no backslash, no `.` or `..` segment, no empty segment;
- unique.

| Path | Kind | In manifest |
| --- | --- | --- |
| `manifest.json` | Manifest (§4), JCS | — (the seal covers it) |
| `seal.intoto.json` | Seal (§6), JCS | — |
| `seal.sigstore.json` | Sigstore bundle over the seal (M2); MAY be absent | — |
| `journal.jsonl` | Hash-chained journal (§5) | yes, role `journal`, mandatory |
| `verdicts.json` | Verdict records | yes, role `verdicts`, mandatory |
| `metrics.json` | Metric records | yes, role `metrics`, mandatory |
| `blobs/sha256/<hex>` | Content-addressed blob; `<hex>` MUST equal the SHA-256 of the content | yes, role `blob` |
| anything else | e.g. `protocol.json`, `system/*.json`, `tasks/*.thr.json`, `adjudications.jsonl`, `decision.json` | yes, with a role from §4 |

Every file other than `manifest.json` and `seal.*` MUST be listed in the manifest. An unlisted file makes the bundle invalid, because nothing seals it.

## 4. Manifest

```json
{"bundle_version":"0.1","members":[{"path":"…","sha256":"<hex>","size":123,"media_type":"application/json","role":"verdicts","mandatory":true}, …]}
```

- `members` is sorted by `path` (byte order), with no duplicates.
- `role` is one of `journal`, `verdicts`, `metrics`, `adjudications`, `protocol`, `system`, `task_health`, `submission`, `decision`, `blob` or `other`.
- **Mandatory roles in v0.1:** `journal`, `verdicts` and `metrics`. Each MUST appear exactly once, with `mandatory: true`. A producer MAY mark further members mandatory; their absence then makes the bundle invalid.
- **A producer MUST refuse to seal** when mandatory evidence is missing (plan §3.4). Incomplete evidence is reported, never sealed as if complete.

## 5. Journal

`journal.jsonl` is UTF-8. It holds one JCS-encoded entry per line, each terminated by `\n`, with no blank lines.

```json
{"seq":0,"prev":"sha256:000…0","event":{…},"hash":"sha256:<hex>"}
```

- `seq` starts at 0 and increases by 1 with each entry.
- `prev` is the `hash` of the previous entry. The first entry's `prev` is the **genesis** reference: `sha256:` followed by 64 zeros.
- `hash` = digest of the JCS form of `{"seq", "prev", "event"}`.
- `event` is an `Event` (`specs/contracts/v0.1/event.schema.json`), and `event.seq` MUST equal `seq`.
- Every `blob_refs` entry in an event MUST resolve to a `blobs/sha256/<hex>` member.
- The **journal head** is the last entry's `hash`, or genesis for an empty journal.

The chain makes a removed, reordered or edited entry detectable. **Tail truncation** is detectable only because the seal records the event count and the head (§6).

## 6. Seal

`seal.intoto.json` is an in-toto **Statement v1** in JCS form:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{"name": "manifest.json", "digest": {"sha256": "<sha256 of manifest.json bytes>"}}],
  "predicateType": "https://github.com/bhargavchintam/aureproof/blob/main/specs/bundle/README.md#predicate-v01",
  "predicate": {
    "bundle_version": "0.1",
    "event_count": 3,
    "journal_head": "sha256:<hex>",
    "completeness": "complete",
    "versions": {"matcher": "0.1.0", "disposition": "0.1.0", "metrics": "0.1.0", "contracts": "0.1", "scoring_spec": "0.1"},
    "generator": {"name": "aureproof", "version": "<package version>"}
  }
}
```

**Predicate v0.1.**
- `completeness` is `complete` or `redacted`. A redacted public bundle is a distinct product from the private complete one (plan §4.2).
- No timestamps are sealed in v0.1. The pure core has no clock, and trustworthy time comes with signing (M2).

The predicate follows in-toto `test-result/v0.1` in spirit. The `predicateType` will move to in-toto's proposed `eval-result` predicate if [in-toto/attestation#575](https://github.com/in-toto/attestation/pull/575) merges (open as of 2026-10-13).

## 7. Validation

`validate(files)` runs every check and reports each one. A bundle is **valid** only if no check fails.

| ID | Check | Fails when |
| --- | --- | --- |
| V1 | Structure | Bad or duplicate paths; `manifest.json`, `seal.intoto.json` or `journal.jsonl` missing; manifest or seal not valid JSON, not matching their schema, or not in JCS form |
| V2 | Members | A manifest member is missing, or its size or digest differs; an unlisted file is present; a blob's path is not its own digest |
| V3 | Journal | A line is not JCS, `seq` is not consecutive, `prev` or `hash` doesn't recompute, an event is invalid, or `event.seq ≠ seq`; event count or head differs from the seal (**truncation**) |
| V4 | Mandatory | A mandatory role is missing, duplicated or not flagged mandatory; a member flagged mandatory is absent |
| V5 | Signature | Reported as `skipped` in v0.1 (signing is M2). Never a pass |
| V6 | Identity | The seal subject is not `manifest.json` with the manifest's digest; `bundle_version` differs between seal and manifest; an event `blob_ref` doesn't resolve; a **trusted seal digest** was supplied and differs |

The validator never stops at the first problem. It reports every failed check, so a reader sees everything that is wrong at once.

## 8. Conformance vectors

`conformance/bundle/v0.1/` holds one valid bundle and invalid variants of it, each derived by one mutation:

- a tampered member;
- a truncated, reordered, edited or re-chained journal;
- a missing mandatory member;
- an unlisted file;
- non-canonical manifest bytes;
- a seal whose count disagrees;
- a forged seal subject;
- a blob whose path is not its digest.

Each vector names the checks that must fail. `scripts/make_bundle_vectors.py` regenerates them deterministically, and a test fails if the committed vectors drift.

## 9. Open questions for the second reviewer

- **B1.** The `predicateType` URI lives under the GitHub repository until a project domain exists. Is that acceptable for v0.1?
- **B2.** Is it right that `verdicts` and `metrics` are mandatory even for a bundle that records only execution, before scoring? The alternative is a separate "execution bundle" profile.
- **B3.** Should v0.1 seal a producer timestamp, unsigned and therefore unverified, for human convenience? This spec says no: unverified time invites misplaced trust.
