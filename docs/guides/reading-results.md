<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Reading results

Issue #56 (guide 2 of 3). What `aureproof score` and `aureproof report` show, and how
to read it without over-reading it. The normative definitions are in
[`specs/scoring/scoring.md`](../../specs/scoring/scoring.md). Guide 3,
[`gate-action.md`](gate-action.md), covers the pass/fail/inconclusive decision.

## Each finding gets one verdict

| Verdict | Meaning |
| --- | --- |
| `confirmed` | Right place, accepted CWE class: it credits a labeled defect (M1; M2 at a source or sink end; M5 when several anchors could match) |
| `duplicate` | A second finding of a defect that was already credited (M4) |
| `refuted` | It points at the repaired focal function or at reviewed-clean scope: a false alarm (M6, M7) |
| `unresolved:class_mismatch` | Right place, wrong class (M3). It goes to adjudication |
| `unresolved:out_of_scope` | Somewhere the labels say nothing about (M8). It goes to adjudication |
| `invalid` | The finding itself is malformed |

**`unresolved` is not `false`.** An unresolved finding is not a false alarm until a
person adjudicates it ([`specs/adjudication`](../../specs/adjudication/README.md)).

## Each episode gets one disposition

The first matching rule wins:

- D1 `evidence_incomplete`
- D2 `infra_failure`
- D3 `safety_refusal`
- D4 `budget_exhausted`
- D5 `agent_error`
- D6 `invalid_output`
- D7 `completed_with_findings`
- D8 `completed_no_findings`

Only D4–D8 are **graded**: their findings enter the quality metrics.

- **Refusals are reported, never counted as misses.** A model that refuses is not
  scored as having found nothing, and a refusal is never retried away.
- **An infrastructure failure is not a miss either.** It is re-run as a new, recorded
  attempt, and it counts against operational completion.
- **`[]` is not the same as no file.** An empty array is `completed_no_findings`. A
  missing `findings.json` is `invalid_output`.

## Every number keeps its denominator

Each metric is shown as *numerator/denominator* and never as a bare percentage. It is
`null`, with a reason, when the denominator is 0.

- **Quality** (over graded episodes): known-defect recall, adjudicated precision
  (shown with the unresolved fraction), **strict confirmed yield** (the primary metric:
  confirmed out of all submitted findings), and the duplicate, invalid-finding and
  scoped false-alarm rates.
- **Operations** (over all scheduled episodes): operational completion, refusal rate,
  infrastructure failure rate, and evidence-incomplete rate.

Read quality and operations separately. A system can be precise and still fail half
its episodes.

## What is excluded, and how you can tell

- **Unhealthy or unknown tasks** are excluded before any metric. Their THR says why
  (`aureproof task validate`).
- **Undefined metrics** stay `null` and are never reported as 0.
- **Spraying does not pay.** Recall alone is never the headline. Strict yield and
  precision fall when an agent flags everything, and the THR `spray_cheat` control
  checks this for every task.

## How far a result generalizes

These are small, synthetic, self-authored tasks. A good score shows a controlled skill
on this suite. It is not a measure of real-world security-review ability. Uncertainty
over a handful of clusters is not a claim about a wider population of code.
