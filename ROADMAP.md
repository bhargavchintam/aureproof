<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Roadmap

The authoritative plan is [`docs/aureproof-plan-v2.md`](docs/aureproof-plan-v2.md);
this is the milestone summary. Effort is in focused days and is a planning
estimate, not a commitment. **The M2 stop/go is the real commitment point.**

v0.1 scope is **frozen** in [`docs/scope.md`](docs/scope.md) (2026-10-27): primary
metric strict confirmed yield (ADR-0006); Claude Code over Anthropic Messages as
the external subject (ADR-0007).

| Milestone | Focus | Exit gate | Kill / pivot |
| --- | --- | --- | --- |
| **M0 Foundations** | Practitioner interviews; repo + OSS kit + CI; worked example (pair #1); Inspect runner spike; Linux host | Interview notes; clone green; spike verdict | No pull → narrow to benchmark + report; bridge can't isolate keys → Docker runner + own proxy |
| **M1 Offline integrity core** | THR / Bundle / Decision specs + schemas + conformance vectors; matcher + metrics; hash-chain + in-toto seal; CLI `validate/score/report` | Golden bundle counts match an independent calculation, offline | Counts disagree → stop, fix the spec |
| **M2 Calibrated slice** | 3 fixture pairs with health controls; difficulty probe; one live episode via the Inspect bridge; signed bundle; offline re-score | One episode linked protocol → model calls → verdict → signed bundle → identical re-score | Baselines saturate → redesign fixtures; no isolated oracle → no live expansion |
| **M3 Benchmark + gate** | ~20 cases (decoys, cross-file, semantic) with adjudication, canaries, private split; Claude Code subject; exact paired gate + GitHub Action; pilot; signed pre-registered protocol | Signed protocol predates the assessment; pilot report with MDE | MDE too large → descriptive claim only |
| **M4 v0.1.0** | Assessment (sanity + close contrasts); report; ABC self-assessment; Croissant card; EEE exporter; SBOM + PEP 740 + DOI; independent reproduction | All release criteria pass (plan §14) | Reproduction fails → no release |
| **M5 Upstream & audit** | NeMo Gym #3675, in-toto #575, Harbor registry; public-benchmark health audit; arXiv report | ≥2 upstream PRs merged or in review | — |

Planned total: ~40–55 focused days.

## Status

Audited **14 October 2026** against default-branch `ca7a936`, GitHub issues/PRs
and local checks. **M0 remains open; M1 is partially implemented; M2 has not
passed.** The unsigned bundle core merged today in PR #30.

Delivered: repository/CI foundation; `authz-001` fixture (#8); accepted Inspect
and attempt-ownership ADRs from the mock spike; findings/event/submission
contracts and SARIF (#11); matcher/dispositions/metrics (#15); unsigned bundle
integrity, journal and in-toto seal (#13). Scoring spec #9 remains draft pending
human review and unresolved choices.

Next: restore the spike after the label-schema migration (#34), harden core
input/conformance behavior (#35–#36), freeze the metric/protocol (#5), name a
reviewer (#31), qualify Linux (#32), finish interviews (#6) and the live spike
(#7), then complete identity/THR/Decision contracts and the offline CLI. Signed
evidence and the production runner follow in M2. **#47 records the M2 stop/go
before benchmark expansion; #66 is the final release gate.**

The expanded backlog has 51 implementation tasks (4 closed, 47 open at audit
time), with estimates, acceptance criteria and numbered dependencies. See the
[ordered execution tracker #67](https://github.com/bhargavchintam/aureproof/issues/67)
and [`docs/project-status.md`](docs/project-status.md) for the full schedule,
verification evidence and workday-count limitations. These tasks decompose the
existing plan; v0.2+ remains deferred.
