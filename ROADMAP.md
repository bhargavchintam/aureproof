<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Roadmap

The authoritative plan is [`docs/aureproof-plan-v2.md`](docs/aureproof-plan-v2.md);
this is the milestone summary. Effort is in focused days and is a planning
estimate, not a commitment. **The M2 stop/go is the real commitment point.**

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

M0 in progress. Done: repository foundation, CI and security settings, the
filed backlog (issues #5–#19), the worked example (fixture pair `authz-001`), and
the Inspect runner spike (ADR-0002/0003 accepted). Remaining for M0: freezing the primary metric
and the agent/protocol choice (#5), the live Claude Code episode (#7),
practitioner interviews (#6), naming a second reviewer (ADR-0005), and the Linux
host. M1 has started with the draft scoring spec
([`specs/scoring/scoring.md`](specs/scoring/scoring.md), #9). Details and status:
[`docs/onboarding-day1.md`](docs/onboarding-day1.md).
