<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Day-1 checklist (milestone M0)

From [`aureproof-plan-v2.md`](aureproof-plan-v2.md) §12. Everything that can be
automated is done; the remaining items need the maintainer.

## Done

- [x] `uv` project; `aureproof` package skeleton in the ports-and-adapters layout (plan §3.9).
- [x] Quality gates: ruff, mypy (strict), pytest, import-linter contracts. Coverage is reported but has no threshold until the scoring core lands (AP-007).
- [x] OSS kit: LICENSE + REUSE, README, CONTRIBUTING (DCO), Code of Conduct 3.0, SECURITY, RESPONSIBLE_USE, CITATION.cff, CHANGELOG, ROADMAP, CODEOWNERS, issue/PR templates.
- [x] CI with SHA-pinned actions and least-privilege tokens: quality gates, gitleaks, CodeQL, Scorecard — green on GitHub.
- [x] Public repository [`bhargavchintam/aureproof`](https://github.com/bhargavchintam/aureproof) with private vulnerability reporting, Dependabot alerts and security updates, secret scanning with push protection, and Discussions enabled.
- [x] Branch protection on `main`: the three CI checks required, 1 approving review, stale approvals dismissed, conversations resolved, no force pushes or deletion. Admins may bypass while there is one maintainer (ADR-0005).
- [x] Backlog filed from [`backlog/issues.toml`](backlog/issues.toml) with `scripts/file_issues.py`: labels, milestones M0–M5, and issues [#5–#19](https://github.com/bhargavchintam/aureproof/issues).
- [x] ADRs 0001–0005; spec stubs (`specs/thr`, `specs/bundle`, `specs/decision`); [`scope.md`](scope.md).
- [x] **Worked example** — fixture pair `authz-001` (missing authorization) with evaluator-only labels, a calibration PoC, an expected-verdict table, and tests that keep labels in sync with the code ([#8](https://github.com/bhargavchintam/aureproof/issues/8)). A semantic defect was chosen for pair #1 because textbook patterns do not discriminate between agents (plan-review C4).
- [x] Interview kit in [`research/`](research/): guide, one-page positioning, mock report, notes template.
- [x] Host readiness check: [`scripts/check_host.sh`](../scripts/check_host.sh) and [`guides/linux-host.md`](guides/linux-host.md).
- [x] Namespace check (2026-10-07): `aureproof` free on PyPI, GitHub, and the .org/.io/.com domains.

## To do (maintainer)

- [ ] **Freeze scope, the primary metric, and the external agent + protocol** in ADRs ([#5](https://github.com/bhargavchintam/aureproof/issues/5), AP-001). This is an M0 issue, and #6 and #9 depend on it.
- [ ] **Name the second reviewer** in `MAINTAINERS.md` and accept ADR-0005 (blocks the M2 calibration gate).
- [ ] **Set the Code of Conduct contact**: a dedicated, non-personal address in `CODE_OF_CONDUCT.md`.
- [ ] **Run 3–5 practitioner interviews** with the kit and record the go / narrow decision ([#6](https://github.com/bhargavchintam/aureproof/issues/6)).
- [ ] **Provision the Linux host** and get all `PASS` from `scripts/check_host.sh`.
- [x] **Day-2 Inspect spike** on `authz-001`: ADR-0002/0003 accepted. Notes: [`research/spike-inspect-day2.md`](research/spike-inspect-day2.md).
- [ ] **Run the live Claude Code episode** to finish spike check 2 ([#7](https://github.com/bhargavchintam/aureproof/issues/7)): put `ANTHROPIC_API_KEY` in `~/.aureproof-spike.env` (mode 600), then run `uv run --extra inspect python spikes/inspect_day2/live.py`.
- [ ] **Set up PyPI Trusted Publishing** before the first `0.1.0a1` release (M1).
- [x] **Dependabot PRs** #1–#4 superseded by the grouped #21 (merged); #23 (pydantic 2.14) merged.
