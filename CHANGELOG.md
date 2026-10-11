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

[Unreleased]: https://github.com/bhargavchintam/aureproof/commits/main
