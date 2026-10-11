<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Task Health Record (THR) — specification

- Spec status: **draft**, unversioned until M1 freezes `thr/v0.1`.
- Normative source: [`../../docs/aureproof-plan-v2.md`](../../docs/aureproof-plan-v2.md) §4.1.

## Purpose

A persistent, machine-readable record that a task's grader works **in a named
environment**, used to **exclude unhealthy tasks at scoring time** (the
exclusion set is frozen before the assessment). Task health is tracked **per
environment**, because an oracle can pass on one runner backend and fail on
another.

## Required controls (findings tasks)

`reference_positive`, `repaired_negative`, `nop`, `spray_cheat`, `malformed`,
`calibration_poc`. A record is `healthy` only if all required controls pass and
a determinism re-run reproduces them; otherwise `unhealthy` or `unknown`.

## To be delivered in M1

- `thr.schema.json` (JSON Schema 2020-12).
- Conformance vectors (healthy / unhealthy / unknown) under `../../conformance/thr/`.
- The reference implementation in `aureproof.contracts` + `aureproof.oracles`.
