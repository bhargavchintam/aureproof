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

As of **29 October 2026** (main `687e3f3`). Gate by gate, with evidence, in
[`docs/release-acceptance.md`](docs/release-acceptance.md).

- **M0:** built, except the interviews (#6), which wait on the maintainer. The
  Linux host is qualified (#32). The maintainer is the reviewer, disclosed as
  self-review (ADR-0005 amendment).
- **M1:** built and passing. The spec issues (#9, #12, #14, #16, #36) wait on the
  maintainer's review, and the `0.1.0a1` alpha (#37) waits on those.
- **M2:** built. Three calibrated pairs, non-saturating probes, the Inspect runner
  and bridge qualification, signing, and one live signed slice that re-scores
  offline ([`research/m2-live-slice.md`](docs/research/m2-live-slice.md)). The stop/go
  decision (#47) waits on the interviews; it is not recorded yet.
- **M3:** drafted, not accepted. The gate, Action and adjudication are built;
  fourteen draft pairs are HEALTHY (six public, eight private). The pilot (#52) is
  blocked until go.
- **M4:** export, Croissant, ABC, SBOM, fault qualification and migration are built.
  The assessment (#54), independent reproduction (#57) and design partner (#62)
  are open.
- **M5:** not started.

The [execution tracker #67](https://github.com/bhargavchintam/aureproof/issues/67)
keeps one valid dependency order; [`docs/project-status.md`](docs/project-status.md)
is the 14 October audit, kept for its schedule and workday-count limitations.
