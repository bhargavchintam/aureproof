<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# M2 live slice protocol

Issue #47. The pre-registered protocol for the M2 live slice
([procedure](../../docs/guides/live-slice.md)), written before any assessment episode
runs and signed by `sign.yml` on main.

| Field | Value |
| --- | --- |
| Protocol identity | `sha256:244fc6d87578873bf95dd90e2bee696e388ffcc2d4fa8142f96650022f5cea2e` |
| Cohort | `authz-001`, `path-001`, `authz-002`, each its own cluster (maintainer decision, 2026-10-29) |
| Configuration A | Claude Code 2.1.287 via Inspect, `anthropic/claude-haiku-4-5-20251001`: `sha256:0358a571a9b66d65fd19d15058408f4d21d07ab3f9b4b5a37f47070b5467a8d3` |
| Configuration B | the same with `anthropic/claude-haiku-5-5`: `sha256:041388e8c706f7621349ff5c29749e0f633ef5250d069f4271f7128c6985afa7` |
| Budget | 400,000 tokens and 900 s per episode, one attempt (Aureproof owns retries) |
| Repetitions | 1 |
| Test | exact sign-flip, α 0.025, margin 0.05, strict confirmed yield B−A |

The THRs are the `aureproof task validate --out` records the protocol names by digest.
They are HEALTHY but self-reviewed and unfrozen (ADR-0005 amendment), and calibrated on
macOS. With three clusters the gate cannot reach `pass` or `fail` (the Decision
Protocol needs at least six), so this slice is an evidence-chain check, not a
comparison. Only configuration A runs in the slice.
