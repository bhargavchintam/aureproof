<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# M2 live slice protocol, revision 2

Issue #47. Replaces [`../m2-slice/`](../m2-slice/) after its first run stopped every
episode as `config:tool_surface_mismatch` (see
[`docs/research/m2-live-slice.md`](../../docs/research/m2-live-slice.md)). The declared
Claude Code tool surface now includes the four task-list tools a real model is
offered, so both system identities changed, and the protocol is named
`m2-live-slice-2`. Nothing else changed: the cohort, the
THRs (still in `../m2-slice/`, named by the same digests), the budget, the
repetitions and the test are those of revision 1.

| Field | Value |
| --- | --- |
| Protocol identity | `sha256:368664cb3802192b43d54b8e61899ca75ddca3b7c2413351f51a54ad69e7c382` |
| Configuration A | Claude Code 2.1.287 via Inspect, `anthropic/claude-haiku-4-5-20251001`: `sha256:3e876b63c2a4787e6a2fbdaea3ab7c65d7f50697ddaa413de9395c802b6b0ad2` |
| Configuration B | the same with `anthropic/claude-haiku-5-5`: `sha256:bdea2bc841f25b96344cdf26d487990dadb0651431194787f1e0faa2f3bb25c9` |

Revision 1 produced no graded episode, so no result was seen before this revision.
The same limits apply: self-reviewed, unfrozen THRs calibrated on macOS, and three
clusters, too few for the gate to reach pass or fail. Only configuration A runs.
