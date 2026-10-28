<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Compatibility and versioning policy

Issues #37 (the M1 part of AP-040) and #58 (`aureproof migrate`).

## What is versioned

| Identifier | Where | Changes when |
| --- | --- | --- |
| Package version | `pyproject.toml` (SemVer; `0.x`) | Any release. In `0.x`, minor releases may change the CLI and the specs |
| Spec versions | `scoring/v0.1`, `bundle/v0.1`, `thr/v0.1`, `decision/v0.1`, `contracts/v0.1` | The normative text or a schema changes meaning |
| Semantics versions | `matcher_version`, `disposition_version`, `metrics_version` | Any rule, parameter or tie-break changes. Each matcher version has exactly one registered parameter profile |
| Scoring identity | `sha256` over the semantics versions and all parameters | Automatically, whenever any of those change. Sealed as `versions.scoring_profile` |
| Record versions | `bundle_version`, `thr_version`, `protocol_version`, `decision_version` in each record | Together with its spec |

Specs are versioned **independently** of the package (plan v2 §4).

## Rules

1. **Readers fail closed on versions they don't know.** A v0.1 reader accepts only
   `0.1` records and rejects anything else with a validation error that names the field.
   From v0.2, readers accept the current version and N−1.
2. **Artifacts are never rewritten in place.** Upgrading a record produces a new record
   (and a new digest). The old one stays verifiable. `aureproof migrate` performs
   upgrades explicitly (see Migrations).
3. **A semantic change is a version change.** Matcher, disposition or metric changes
   bump their version, add a parameter profile, and update the golden vectors in a
   reviewed PR. Results under different scoring identities are never pooled, and an
   offline re-score MUST use the sealed identity.
4. **Specs marked *draft* may change before the second review** (ADR-0005). Every
   change is recorded in `CHANGELOG.md`. Once a spec version is released in a tagged
   package, its meaning is frozen.
5. **Conformance vectors are the contract.** A change that alters an expected outcome
   in `conformance/` is a semantic change (rule 3).

## Enforcement

`tests/test_compatibility.py` checks that unknown `bundle_version`, `thr_version`,
`protocol_version`, `decision_version`, `matcher_version` (unregistered parameters) and
seal `predicateType` values are rejected, and that the scoring identity changes when any
semantic version changes.

## Migrations

`aureproof migrate SOURCE --out NEW` upgrades one record into a new file and writes
`NEW.provenance.json` next to it. That file holds the source's digest, the versions, the
declared losses and the tool version. The command never edits its input or
overwrites anything, and it refuses a file inside a sealed bundle: sealed evidence is
re-scored into a new bundle, never migrated. An unknown or current version is refused
by name.

| From | To | Losses | Conformance |
| --- | --- | --- | --- |
| `aureproof.labels/draft-0` | `aureproof.labels/v0.1` | The draft focal negative had only its site anchor. v0.1 lists every anchor of the repaired defect, so source and sink anchors must be added by hand. Until they are, a source-end finding on the repaired variant is unresolved rather than refuted | `conformance/migrations/labels-draft-0-to-v0.1`: the real authz-001 history (`d85a543` to `d417444`). The migrated record matches the hand migration except for that loss (`tests/contracts/test_migrate.py`) |

**Initial-version limit.** `bundle_version`, `thr_version`, `protocol_version`,
`decision_version`, the scoring semantics and the `contracts/v0.1` records have only
one released version, 0.1. They have no N−1 to validate or migrate from, so the
policy for them is rule 1 (fail closed) until a 0.2 exists. A 0.2 must come with its
migration and with N−1 vectors.

