<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0005: A second reviewer is required for calibration and release gates

- Status: accepted with an amendment (2026-10-29): the maintainer reviews, and self-review is disclosed
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

## Amendment (2026-10-29)

No second person is available. The maintainer decided to act as the reviewer.
What this changes, and what it does not:

- Spec and label reviews (#9, #12, #14, #36, the reviewer packet in
  `docs/maintainer-actions.md`) are done by the maintainer and recorded as
  **self-reviews** on each issue.
- The THR freeze rule stays: a record is frozen only with an
  `independent_reviewer` (`specs/thr/README.md` §5). The maintainer is recorded
  as `author`, so THRs stay unfrozen and every report flags its tasks as not
  independently reviewed.
- Co-adjudication κ needs two people. Until there are two, reports say that κ
  is not available rather than report a self-agreement figure.
- Revisit as soon as a second person can review; then the original decision applies.
