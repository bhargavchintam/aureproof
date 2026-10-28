<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Task Health Record (THR) specification

- Spec: `thr/v0.1`. Status: **draft, pending a second review** (issue #12, AP-035;
  acceptance also waits on #9).
- Normative source: plan v2 §4.1. This document refines it and takes precedence.
- Schema: [`v0.1/thr.schema.json`](v0.1/thr.schema.json), generated from
  `aureproof.contracts.thr`. Vectors: [`conformance/thr/v0.1/`](../../conformance/thr/v0.1/).

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Purpose

A persistent, machine-readable record that a task's grader works **in a named
environment**. It decides **scoring-time exclusion**, and the exclusion set is frozen
before the assessment. Health is tracked per environment, because an oracle can pass
on one runner backend and fail on another (Harbor #136).

## 2. Record

| Field | Meaning |
| --- | --- |
| `thr_version` | `"0.1"` |
| `task` | `task_id`, `task_revision`, `task_identity` (`TaskSpec.identity`) |
| `environment` | `runner`, `runner_version`, `image_digest`, `platform` |
| `scoring_identity` | The scoring semantics the controls ran under (`aureproof.scoring.scoring_identity`) |
| `controls[]` | `{kind, variant?, input_digest, expected, observed, passed, run_ids, note?}`. `passed: null` means the control could not run |
| `determinism` | `{rerun_ids, reproduced}`. Every control is re-run, and the outcomes MUST be identical. `null` means no re-run |
| `difficulty_probe` | `{bandit, single_shot_model}`, each `{probe, system_identity, solved, detail?}` or `null` (§6) |
| `status`, `status_reason` | Derived (§3); never asserted by hand |
| `known_limits[]` | Human-readable caveats |
| `reviewed_by[]`, `frozen_at` | Reviewers `{name, role: author \| independent_reviewer}`; freeze time (UTC) |
| `canary_id`, `provenance` | Contamination canary; `{authorship, license}` |

## 3. Required controls and the health derivation

| Control | Passes when |
| --- | --- |
| `label_lint` | Label lint L1–L4 (§4) reports no problems against the code the agent sees |
| `reference_positive` | A label-perfect submission confirms every defect present in the variant |
| `repaired_negative` | A finding at the focal anchor on the repaired variant is `refuted` (M6) |
| `nop` | An empty submission gives known-defect recall 0 |
| `spray_cheat` | A finding at every function with every accepted CWE gets recall ≈ 1, while **strict confirmed yield and precision collapse**. If any headline metric rewards spraying, the metric design is broken and the task is unhealthy |
| `malformed` | Invalid JSON gives `invalid_output` |
| `calibration_poc` | The evaluator PoC triggers on the vulnerable variant and not on the repaired one; irrelevant and malformed triggers don't count |

**Derivation** (`aureproof.contracts.thr.derive_status`). The first matching rule wins:

1. Any control has `passed: false` → **unhealthy** (the reason lists the failed controls).
2. `determinism.reproduced` is `false` → **unhealthy**.
3. A required control is missing or has `passed: null` → **unknown**.
4. `determinism.reproduced` is `null` → **unknown**.
5. Otherwise → **healthy**.

A record whose `status` differs from the derived status is invalid. Health can't be
asserted by hand.

## 4. Label lint (control `label_lint`)

`aureproof.contracts.labels_lint.lint_labels(labels, agent_views, spans)`:

- **L1:** within a file, each anchored or scoped symbol's final dotted component names
  exactly one symbol.
- **L2:** no anchor lies inside reviewed-negative scope for the same variant.
- **L3:** every anchor and scope file exists in that variant's agent view, and its lines
  are within the file. When symbol spans are supplied (read from the code by
  `aureproof.oracles.python_spans`, which parses and never imports), each anchor's
  `line_range` MUST equal the symbol's real span. **Label drift fails here.**
- **L4:** every defect accepts at least one CWE.

## 5. Exclusion policy

`aureproof.scoring.health.partition_by_health(episodes, records, protocol_frozen_at)`:

- **Only records frozen before the protocol freeze decide exclusion.** A task whose
  pre-registered record is `unhealthy` or `unknown` is **excluded**: its episodes leave
  the cohort before metrics, and it is reported as a dataset-health finding.
  **An unhealthy task never becomes an agent false positive.**
- A health finding made **after** the protocol freeze is reported as **exploratory** and
  not applied. The task stays in the primary analysis, so exclusions can't be chosen
  after seeing results.
- A task with no frozen record stays in the cohort and is flagged.
- A record MAY be frozen only with at least one `independent_reviewer` (ADR-0005).

## 6. Difficulty probe

`difficulty_probe` records whether a pattern scanner (Bandit, via SARIF) or a single-shot
model already solves the task. It does not affect health. It is **required before
benchmark expansion** (the M2 gate, #44 and #47). A task that both baselines solve does
not discriminate between agents and should be redesigned (plan-review C4).

## 7. Open questions for the second reviewer

- **H1.** Should `unknown` tasks be excluded like `unhealthy` ones (this draft says yes),
  or kept with a warning?
- **H2.** Is a single determinism re-run enough, or should the protocol set the count?
