<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Evidence Bundle — specification

- Spec status: **draft**, unversioned until M1 freezes `bundle/v0.1`.
- Normative source: [`../../docs/aureproof-plan-v2.md`](../../docs/aureproof-plan-v2.md) §4.2.

## Purpose

A self-contained, verifiable record of an evaluation: a manifest over
content-addressed artifacts, a hash-chained append-only journal, verdicts,
metrics, adjudications, and a decision — sealed and signed so a third party can
**validate and re-score it offline**.

## Standards

- Canonical JSON via **RFC 8785**; digests are SHA-256.
- The seal stores the journal event count and head hash (so tail truncation is detectable).
- The seal is an **in-toto Statement v1**; the predicate aligns with in-toto
  `test-result/v0.1` and tracks the proposed `eval-result/v0.1` (in-toto PR #575).
- Signed with **Sigstore** (sigstore-python).

## To be delivered in M1 (seal) / M2 (signing)

- `bundle.schema.json` (manifest + seal).
- Conformance vectors: valid, tampered, truncated, and missing-mandatory-member.
- The reference implementation in `aureproof.bundle` (pure) + CLI I/O.
