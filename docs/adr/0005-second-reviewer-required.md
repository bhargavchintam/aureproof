<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0005: A second reviewer is required for calibration and release gates

- Status: proposed (needs a named reviewer; see MAINTAINERS.md)
- Date: 2026-10-07
- Deciders: lead maintainer

## Context

Several gates — oracle calibration, the frozen assessment, and release — assume
an independent check. With a single maintainer those gates are self-certified,
which undermines the project's core claim that verdicts are independently
reviewable. Adjudication quality also needs an inter-rater agreement measure.

## Decision

Name a second reviewer before the M2 calibration gate. That reviewer (a) signs
off the calibration of each shipped task-health record, (b) independently
reproduces at least one metrics table before release, and (c) co-adjudicates
≥20% of unresolved findings so Cohen's κ can be reported (plan §5.7). Until one
is named, gated milestones are blocked and this ADR stays `proposed`.

## Consequences

- Easier: credible, non-self-certified gates; a reported agreement statistic.
- Harder: a scheduling dependency on another person; mitigated by keeping the reviewer's tasks small and asynchronous.
- Revisit: when a reviewer is named (promote to `accepted`), or if the project gains regular co-maintainers.
