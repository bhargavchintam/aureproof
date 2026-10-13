<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims
to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (0.x: the
public API and the specs may change between minor versions).

## [Unreleased]

### Added
- Day-1 repository foundation (milestone M0): uv project, `aureproof` package
  skeleton in a ports-and-adapters layout, and the `aureproof --version` CLI.
- Quality gates: ruff (lint + format), mypy (strict), pytest + coverage, and
  import-linter contracts enforcing the pure-core boundary.
- Open-source kit: Apache-2.0 license, REUSE compliance, Contributor Covenant
  3.0, DCO-based contributing guide, security and responsible-use policies,
  CITATION.cff, issue/PR templates, and CODEOWNERS.
- CI with SHA-pinned actions and least-privilege tokens: quality gates, secret
  scanning, CodeQL, and OpenSSF Scorecard; weekly Dependabot updates.
- Scaffolding for the three specs (`specs/thr`, `specs/bundle`, `specs/decision`)
  and the initial ADRs.
- Worked example: fixture pair `authz-001` (missing authorization) with decoys,
  evaluator-only labels, a calibration PoC, an expected-verdict table, and tests
  that fail if labels drift from the code or evaluation writes into the fixture tree.
- Backlog as data (`docs/backlog/issues.toml`) and an idempotent filer
  (`scripts/file_issues.py`) for labels, milestones, and issues.
- Practitioner interview kit (`docs/research/`) and a Linux evaluation-host
  check (`scripts/check_host.sh`, `docs/guides/linux-host.md`).
- Dependabot groups GitHub Actions updates into a single pull request.
- Day-2 Inspect runner spike (`spikes/inspect_day2/`, issue #7). Adds an optional
  `inspect` extra with exact pins, collect-then-match grading of `findings.json`,
  a bridge probe for no-network and key isolation, a one-command live-run harness
  with a key-leak scan, and a Docker-gated regression test. ADR-0002 (Inspect
  first) and ADR-0003 (Aureproof owns attempts) are accepted.
- Draft scoring specification `scoring/v0.1` (`specs/scoring/scoring.md`, issue #9):
  matcher rules M1–M9 with normalization and validity rules, the episode
  disposition decision list, metric definitions with explicit denominators and
  undefined cases, and 41 golden vectors plus 3 cohort metric vectors
  (`conformance/scoring/v0.1/golden.json`) with integrity tests.
- Data contracts (`aureproof.contracts`, issue #11): findings, labels,
  verdicts, dispositions, episode signals, metric records, events with
  `observation_source` trust tiers, and submissions. Includes SARIF 2.1.0
  export and import with a property-based round-trip test, generated JSON Schema
  2020-12 files in `specs/contracts/v0.1/` with a drift check, and conformance
  vectors checked against both the models and the schemas.
- The v0.1 oracle (`aureproof.scoring`, issue #15): a pure, deterministic label
  matcher (rules M1–M9), strict submission parsing, the episode disposition
  decision list, and cohort metrics with explicit support. All 44 golden vectors
  and the `authz-001` expected-verdict table pass, along with Hypothesis
  invariants (duplicates never change recall; precision is undefined exactly when
  confirmed + refuted = 0; spraying collapses strict confirmed yield).
  The coverage gate is now 90%.

### Changed
- `MetricRecord` gains `kind` (`proportion` or `rate`): the scoped false-alarm
  rate can exceed 1.
- `authz-001` labels migrated to the v0.1 label schema (`variants[]`; the focal
  negative lists its site and source anchors).
- Dependencies: grouped GitHub Actions updates (#21) and pydantic 2.14.0 (#23).

[Unreleased]: https://github.com/bhargavchintam/aureproof/commits/main
