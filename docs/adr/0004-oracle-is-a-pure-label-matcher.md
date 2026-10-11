<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# ADR-0004: The v0.1 oracle is a deterministic label matcher

- Status: accepted
- Date: 2026-10-07
- Deciders: lead maintainer

## Context

The original plan both accepted non-executable structured findings in v0.1 and
specified a restricted test target that executes submissions. These contradict:
there is nothing executable in a v0.1 finding. Separately, reading a verdict
from any file that untrusted code can write is unsafe (demonstrated by Harbor
#2551 and #1779).

## Decision

The v0.1 oracle is `match(findings, labels, matcher_version)` — a pure,
deterministic function in the trusted controller, needing no network and no
execution. Evaluator-authored **calibration PoCs** (trusted inputs) prove each
labeled defect fires on the vulnerable variant and not on the repaired one.
Agent-submitted PoCs are stored as evidence but **not executed** until v0.2,
when they run under the separate-verifier confinement of ADR-0002. Verdicts are
never read from agent-writable files.

## Consequences

- Easier: v0.1 grading is deterministic, offline, and trivially re-scorable; the hostile-execution surface moves to v0.2.
- Harder: the matching rules become the real measurement and must be specified exhaustively with golden examples (plan §5.4, AP-005).
- Revisit: v0.2 adds the `poc_verifier` oracle and executable re-verification.
