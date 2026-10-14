<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Project status and execution plan

Audited **14 October 2026**, using America/Los_Angeles dates. The authoritative
design is [`aureproof-plan-v2.md`](aureproof-plan-v2.md), prepared 6 October.
The public [execution tracker #67](https://github.com/bhargavchintam/aureproof/issues/67)
contains one valid dependency order for working through the issues.
[`backlog/issues.toml`](backlog/issues.toml) remains the filing source of truth.

## Current position

**M0 is incomplete, M1 is partially implemented, and the M2 stop/go has not
passed.** Foundations, one fixture pair, findings contracts, scoring and
unsigned bundle integrity exist. The CLI currently provides help/version
only. There is no production runner, complete THR, decision implementation,
Sigstore verification, assessment or independently reproduced result.

The review covered tracked application source, tests, schemas/conformance,
fixtures, spikes, scripts, workflows, governance, planning and research docs,
plus Git history and live GitHub issues/PRs. No live inference, provisioning,
outreach or release publication was performed during this audit. External
landscape/provider statements in the original plan were not revalidated;
their scheduled policy/upstream tasks must check current primary sources.

GitHub's default branch is `ca7a9364db44ea98a1446bb19ce9a2263ecb7830`.
The original 15 issues had 4 closed and 11 open. Added **36 missing task issues**
(#31–#66) and updated all 15 existing bodies; the resulting backlog has
**51 tasks: 4 closed, 47 open** at audit time. Tracker #67 is separate from
that count. Later implementation PRs will change these snapshot counts.

## How many days have been completed?

There are **four development author dates: October 10, 11, 12 and 13**.
Commit/merge delivery dates span October 10–14; the latest bundle work was
authored October 13 and merged October 14. Four calendar days have elapsed
since the first scaffold on October 10. None of this measures focused effort:
there is no timesheet, hours log or accepted milestone-effort ledger.

| Development date | Recorded artifacts | Acceptance limitation |
| --- | --- | --- |
| October 10 | Scaffold, OSS/CI kit, backlog, interview kit, `authz-001` pair | Interviews, scope freeze, reviewer and Linux host remain open |
| October 11 | Inspect mock/reference spike; ADR-0002/0003 accepted | No real Claude Code submission; no Linux qualification |
| October 12 | Scoring draft/vectors, findings contracts, SARIF, matcher authored | Scoring review and identity/health/protocol contracts remain open |
| October 13 | Matcher merged; unsigned bundle core authored | Offline CLI and signatures remain absent |
| October 14 | Bundle core merged in [PR #30](https://github.com/bhargavchintam/aureproof/pull/30) | Merge delivery does not establish another full focused workday |

The original Day-1–Day-6 sequence has substantial technical artifacts, but
Day 3's frozen semantics/STRIDE/protocol work is incomplete. Neither the
Day-7 offline gate nor the Day-10–12 signed vertical slice is complete.
Do not report “six days finished,” subtract four from the effort budget,
or infer completion percentages from unequal issue sizes.

## Planned schedule

These are the plan's **cumulative focused-day checkpoints**, not calendar
deadlines or durations to add together. One focused day assumes roughly six
productive hours. Overall estimate: **40–55 focused days, about 240–330 hours**.
Availability, reviewer/partner waits, host setup and upstream review determine
calendar time. No milestone due dates or task assignees are currently set.

| Milestone | Planned cumulative effort | Scheduled outcome | Current status |
| --- | --- | --- | --- |
| M0 Foundations | 5–6 days | Demand decision, scoped protocol/metric, worked example, runner spike, Linux host and reviewer | Open; technical foundation exists |
| M1 Offline integrity core | 12–16 days | Three specs/contracts, exact offline counts, safe CLI/report, threat matrix and alpha | Partial; contracts/scoring/unsigned bundle core merged |
| M2 Calibrated slice | 20–26 days | Three healthy pairs, probes, production reference episode, signed evidence and identical offline re-score | Not accepted; [stop/go #47](https://github.com/bhargavchintam/aureproof/issues/47) is the commitment point |
| M3 Benchmark + gate | 30–38 days | About 20 cases, at least 8 clusters, external agent, adjudication, 36-episode pilot/MDE, signed protocol and Action | Not started as an accepted milestone |
| M4 v0.1.0 | 36–46 days | Sanity/close assessments, release artifacts, partner validation and independent reproduction | Not started; [release gate #66](https://github.com/bhargavchintam/aureproof/issues/66) |
| M5 Upstream & audit | Additional 5–8 days, overlapping M3 onward | Health audit, at least 2 upstream PRs under active review/merged, arXiv and registration | Future work |

The first-12-days table is an accelerated original task sequence. The larger
cumulative estimates and acceptance gates govern this status report. Task
estimates in the backlog are planning assumptions, with overlap; they are not
an earned-effort calculation or a new calendar commitment.

## Completed deliverables

- [#8 / AP-010](https://github.com/bhargavchintam/aureproof/issues/8): one synthetic vulnerable/repaired pair with labels, calibration PoC, decoys, canaries and drift checks.
- [#11 / AP-004](https://github.com/bhargavchintam/aureproof/issues/11): findings, labels, events, submissions, dispositions and metric contracts; eight exported schemas; SARIF mapping.
- [#15 / AP-007](https://github.com/bhargavchintam/aureproof/issues/15): pure matching/dispositions/metrics, 41 episode golden cases, three cohort cases and invariants.
- [#13 / AP-036](https://github.com/bhargavchintam/aureproof/issues/13): RFC 8785 digests, content-addressed in-memory blobs, hash chain, in-toto seal and tamper/truncation validation. Signatures and safe filesystem adapters remain follow-ups.
- Foundation (AP-033, delivered without creating a retrospective open issue): project layout, pinned CI, security/OSS kit, research kit and host-check scripts.

Scoring spec [#9](https://github.com/bhargavchintam/aureproof/issues/9) is drafted
and executable but remains open for independent review and Q1–Q5 decisions.
Completed implementation does not imply that its earlier scope/review
dependencies were accepted; the queue makes those outstanding decisions clear.

## Next work in dependency order

Each issue contains its own numbered prerequisites, estimate and definition of
done. Tracker #67 lists all 47 open tasks in one valid topological order. If a
person-dependent item is waiting, work on another issue whose prerequisites
are complete. Drafting can start early; gate acceptance requires the evidence.

| Stage | Issues and deliverables |
| --- | --- |
| Repair the current measuring path | **#34 first**: spike/current-label compatibility and no-cost CI lane. **#35 next**: bounded JSON and bundle conformance. #36: scoring parameter/version identity and supported metric values, after reviewed semantics |
| Finish M0 decisions | #5 metric/agent/protocol freeze; #31 reviewer; #32 Linux host; #33 project contact/license provenance; #6 interviews/go-narrow; #7 real Claude Code spike after repair and qualification |
| Complete M1 | #9 scoring review; #10 identity schemas; #12 THR spec; #14 Decision spec/exact statistics; #17 threat/control matrix; #18 provider terms; #16 offline CLI, safe persisted bundles and report; #58 compatibility-policy portion; #37 independent offline alpha gate/Trusted Publishing |
| Build M2 slice | #19 durable attempts/recovery; #38 calibration THR plus task validate/fixture CI; #39 production Inspect adapter; #40 artifact collection limits; #42 bridge controls; #43 reference subject; #41 pairs 2–3; #44 difficulty probes; #45 private split/canaries; #46 signatures; **#47 stop/go** |
| Build M3 benchmark/gate | #48 production Claude Code subject; #49 about 20 cases/8 clusters; #51 adjudication; #50 comparison report; #53 CLI/Action gate; #52 pilot/MDE and signed pre-registration |
| Qualify M4 release | #54 assessment; #55 faults; #58 version/migration policy; #59 EEE; #60 dataset/RAI card; #61 ABC; #56 release-candidate docs/provenance; #62 partner own-log validation; #57 independent reproduction; **#66 final release** |
| Follow through M5 | #63 public health audit; #64 coordinated upstream contributions; #65 paper and inspect_evals registration |

The code-only repairs #34 and #35 are ready independently of missing human
decisions. Maintainer action is required to choose the metric/protocol, name
the reviewer, supply a Linux host and contact, organize interviews/partner
participation, and configure publishing. Their issues state the required
evidence; this audit does not invent identities, budgets or consent.

## Findings behind the early repair issues

| Issue | Reproduced or inspected evidence | Required outcome |
| --- | --- | --- |
| #34 | Spike matcher reads `defect['variant']` and `focal_negative['anchor']`; current labels use arrays. Both variant calls raise `KeyError: 'variant'`. Ordinary CI skips the Inspect module | Current core/label semantics in spike; pure regression checks in ordinary CI; mock/Docker qualification kept distinct from live results |
| #35 | Bundle `validate({'manifest.json': b'NaN'})` throws a canonicalization exception; oversized JCS integers/lone surrogates also escape. Depth-10,000 JSON below the byte cap throws `RecursionError`. Raw-event hashing is changed by model defaults, and builder mandatory overrides can emit a bundle its validator rejects | Failed validation/disposition rather than controller exceptions; raw canonical event hash interoperability; builder invariants and published bundle schemas |
| #36 | Custom `MatcherParams(line_tolerance=100)` changes verdicts under the same recorded version. A metric with 1/2 support and value 100 currently validates | Version/profile fixes effective semantics; finite, supported metric values with proportion/rate distinctions |

These are known limitations tracked for repair; this PR does not implement
those production changes. The passing existing tests do not cover these inputs.

## Verification and limits

- `uv run pytest`: **271 passed; one integration module skipped** because `inspect_ai` is not installed; **96.22% coverage** on the final verification run. This is offline/core evidence, not a production isolation result.
- Ruff lint/format, strict mypy, both import-linter contracts and REUSE 3.3 pass. Backlog tests verify unique IDs/titles, known labels/milestones, actionable tasks and an acyclic full dependency graph.
- Latest default-branch [CI](https://github.com/bhargavchintam/aureproof/actions/runs/38542780432), [CodeQL](https://github.com/bhargavchintam/aureproof/actions/runs/38542780647) and [Scorecard workflow](https://github.com/bhargavchintam/aureproof/actions/runs/38542780475) succeeded. Workflow success alone does not establish a Scorecard score of at least 8.
- October 11 spike evidence uses `mockllm/model` in dry-run mode and records `claude_code_wrote_findings=false`. It is plumbing evidence, not a live assessment. The current host is macOS/Docker Desktop; required Linux controls are unqualified.
- Research files are a kit and an explicitly invented mock, not interview or assessment evidence. Mock episode arithmetic was corrected to 42 per system and its cluster contrast clarified during this documentation update.
- GitHub Project-board inspection was unavailable because the CLI token lacks `read:project`. Issues, milestones and tracker #67 provide an ordered workflow without changing account permissions.

## Scope and release decisions

M2 go is required before expanding the benchmark; failed controls or saturated
fixtures trigger redesign. Closing the interview issue with narrow/rethink
does not authorize the unchanged scope: go must support the current scope,
or narrow must produce a reviewed scope/roadmap/backlog amendment. Rethink
blocks expansion until resolved. Pilot MDE can make the eventual claim descriptive.
The signed protocol must precede assessment. Missing evidence, low power or
incomplete adjudication cannot become pass. Independent reproduction failure
blocks the release. #66 consolidates every plan §14 acceptance criterion;
preparing a candidate in #56 does not authorize final publication early.

AP-040/#58 includes an M1 compatibility-policy portion, required by the alpha
gate #37, and M4 migration work. Alpha need not wait for the entire migration
issue to close if the policy evidence is accepted.
EEE/#59 and Croissant/#60 retain the original P1 labels but remain tracked in
M4 because the roadmap explicitly includes them; minimal license/RAI metadata
is required by §14. Any future deferral needs an explicit scope amendment,
not a silent release-gate omission.

Deferred work stays visible in the original plan: ATIF (AP-026), NAT (AP-027),
Harbor and executed PoCs (AP-012H/013b), real-world subset (AP-028), patch
grading, injection and scripted chat (AP-029–031). Those future frameworks and
task families were not filed as immediate execution work. Heavy governance,
OTel and a hosted dashboard remain on demand or out of scope.
