<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Decision Protocol — specification

- Spec status: **draft**, unversioned until M1 freezes `decision/v0.1`.
- Normative source: [`../../docs/aureproof-plan-v2.md`](../../docs/aureproof-plan-v2.md) §4.3.

## Purpose

A pre-registered, signed description of an A/B comparison that yields a
three-way outcome: **pass / fail / inconclusive**. Signed before the first
assessment episode so the claim cannot be chosen after seeing the data.

## Method

- Estimand: contrast B − A on the primary metric over the frozen healthy cohort,
  summarized as the mean of cluster-level differences.
- Test: **exact paired sign-flip permutation** over the *k* clusters (all 2^k
  assignments); confidence interval by test inversion; Wilson intervals per
  configuration.
- Decision at level 1−2α with margin δ: **pass** if the CI lower bound > −δ,
  **fail** if the upper bound < −δ, else **inconclusive**.
- Power floor: a decisive outcome at α = 0.05 needs **≥6 independent clusters**
  (with k ≤ 5 the smallest exact two-sided p is ≥ 0.0625). The pilot's minimum
  detectable effect is recorded in the protocol.

## To be delivered in M1 (schema + test) / M3 (gate + Action)

- `decision.schema.json`; the pure implementation in `aureproof.stats`.
- Conformance vectors with hand-checked exact p-values and intervals.
