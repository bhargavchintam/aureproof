# MOCK REPORT — illustrative only

> **This is a mock for user interviews. Every number below is invented to show
> the report's shape. Aureproof has produced no evaluation results yet.**

## Decision: **INCONCLUSIVE** — candidate B vs baseline A

| Item | Value |
| --- | --- |
| Protocol | `protocols/mock-v0.yaml`, signed before the first episode |
| Primary metric | Strict confirmed yield (confirmed findings / all submitted findings) |
| Margin δ | 0.05 (non-inferiority) |
| Cohort | 14 healthy tasks in 8 independent clusters; 2 tasks excluded as **unhealthy** before the run |
| Repetitions | 3 per task per system — 42 scheduled episodes per system |
| Result | B − A = +0.04, exact 90% CI [−0.07, +0.15] → **inconclusive** (the CI crosses −δ) |

**Why inconclusive:** with 8 clusters the interval is wide; the data cannot rule
out a regression larger than the margin. This is reported as inconclusive, not
as a win for B.

## Task health (frozen before the assessment)

| Task | Status | Reason |
| --- | --- | --- |
| authz-001 … (13 more) | healthy | All controls pass, including the no-op and "flag everything" controls |
| pathx-003 | unhealthy | Reference finding not confirmed on runner backend X |
| cmdx-002 | unhealthy | Repaired variant still triggers the calibration PoC |

## Outcomes per system (all scheduled episodes accounted for)

| Disposition | A | B |
| --- | --- | --- |
| Completed with findings | 35 | 37 |
| Completed, no findings | 3 | 1 |
| Safety refusal (reported, not a miss) | 2 | 1 |
| Infrastructure failure | 2 | 3 |

| Finding verdicts | A | B |
| --- | --- | --- |
| Confirmed | 58 | 66 |
| Refuted (false alarms) | 31 | 29 |
| Duplicate | 9 | 12 |
| Unresolved → adjudication | 4 | 5 |

## Per-cluster differences (B − A)

`+0.10, −0.04, +0.08, 0.00, +0.12, −0.06, +0.05, +0.07`

The reported contrast averages these eight cluster differences. The finding
counts above are pooled descriptive totals, so subtracting their pooled
yields does not reproduce the cluster-averaged contrast. The interval is an
invented illustration, not a calculation or an observed result.

## Evidence

- Bundle digest: `sha256:…` · signature verified with Sigstore · re-score offline:
  `aureproof score bundle/ --offline` reproduces every number above.
- Every finding links to the controller-observed model calls and the submitted
  artifact; agent-reported tool traces are labeled as such.
