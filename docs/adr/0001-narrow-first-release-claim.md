<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0001: Narrow the first-release claim to security discovery

- Status: accepted
- Date: 2026-10-07
- Deciders: lead maintainer

## Context

The original blueprint tried to cover discovery, reproduction, repair, chat,
multiple frameworks, telemetry exports, and a UI at once. A solo maintainer
cannot make all of that defensible, and breadth competes with the one thing
that gives the project credibility: measurement validity.

## Decision

v0.1 makes one promise: reviewable, reproducible evaluation of **security-defect
discovery** on self-authored synthetic Python fixtures, graded by a trusted
oracle, sealed as signed evidence, and compared under a pre-registered protocol.
Everything else (PoC reproduction, patch grading, chat, real CVEs, multi-agent)
is staged behind acceptance gates in later versions.

## Consequences

- Easier: a demonstrable vertical slice; a clear release gate; honest claims.
- Harder: resisting scope creep — mitigated by the rule "no P0 added without one removed".
- Revisit: when v0.1 gates pass, expand to v0.2 (real reproduction) per the roadmap.
