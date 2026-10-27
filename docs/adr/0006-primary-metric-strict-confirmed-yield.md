<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0006: Strict confirmed yield is the primary metric

- Status: accepted
- Date: 2026-10-27
- Deciders: lead maintainer (issue #5, AP-001)

## Context

The decision gate and the pre-registered protocol test **one** primary
estimand; everything else is reported alongside but cannot decide a release.
The candidates are defined in [`specs/scoring/scoring.md`](../../specs/scoring/scoring.md) §6.

- **Known-defect recall** rewards spraying: a finding at every function with every
  accepted CWE reaches recall ≈ 1 (golden vector `S-01`; THR `spray_cheat`).
- **Adjudicated precision** excludes unresolved findings from its denominator, so
  it moves when adjudication catches up and is unstable before it does.
- **Strict confirmed yield** = confirmed / all submitted findings. Duplicates,
  invalid findings, refuted and unresolved findings all stay in the denominator.
  Spraying collapses it (`S-01`: 3/10; synthetic spray ≤ 0.05).

## Decision

The primary metric for v0.1 is **strict confirmed yield** (`strict_confirmed_yield`,
`metrics_version` 0.1.0), computed per configuration over graded episodes and
compared as the mean of cluster-level differences (plan §4.3).

Reported alongside it, never as substitutes: known-defect recall, adjudicated
precision with the unresolved fraction, scoped false-alarm rate, duplicate and
invalid rates, operational completion, refusal rate, infrastructure-failure rate,
and evidence-incomplete rate.

## Consequences

- Easier: the headline number cannot be gamed by volume, and it matches the
  project's precision-first claim.
- Harder: an agent that finds nothing scores yield *undefined* (no submissions),
  not 0. The report must show recall and completion next to yield so that silence
  is visible. The Decision Protocol (AP-037) must state how undefined yield enters
  a cluster difference.
- Revisit: if the pilot (AP-021) shows yield is too noisy at the planned size,
  amend the protocol *before* the assessment; never after.
