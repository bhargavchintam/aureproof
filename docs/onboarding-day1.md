<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Day-1 checklist (milestone M0)

From [`aureproof-plan-v2.md`](aureproof-plan-v2.md) §12. Everything that can be
automated for the initial foundation is done; the remaining items need the
maintainer. This is the historical foundation checklist; current project-wide
progress and work order are in [`project-status.md`](project-status.md).

## Done

- [x] `uv` project; `aureproof` package skeleton in the ports-and-adapters layout (plan §3.9).
- [x] Quality gates: ruff, mypy (strict), pytest, import-linter contracts. Coverage must stay at or above 90% (enforced since AP-007).
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

The open items, each as one action with what it unblocks, are in
[`maintainer-actions.md`](maintainer-actions.md).

- [x] **Freeze scope, the primary metric, and the external agent + protocol** in ADRs ([#5](https://github.com/bhargavchintam/aureproof/issues/5), AP-001). This is an M0 issue, and #6 and #9 depend on it.
- [x] **Reviewer decided** (2026-10-29): the maintainer self-reviews, disclosed in `MAINTAINERS.md` and the ADR-0005 amendment ([#31](https://github.com/bhargavchintam/aureproof/issues/31)). THR freezing still needs an independent reviewer.
- [x] **Set the Code of Conduct contact** (2026-10-29) and reconcile license provenance ([#33](https://github.com/bhargavchintam/aureproof/issues/33)).
- [ ] **Run 3–5 practitioner interviews** with the kit and record the go / narrow decision ([#6](https://github.com/bhargavchintam/aureproof/issues/6)).
- [ ] **Provision the Linux host** and get all `PASS` from `scripts/check_host.sh` ([#32](https://github.com/bhargavchintam/aureproof/issues/32)).
- [x] **Day-2 Inspect spike** on `authz-001`: ADR-0002/0003 accepted. Notes: [`research/spike-inspect-day2.md`](research/spike-inspect-day2.md).
- [x] **Repair and re-run the spike with current labels** ([#34](https://github.com/bhargavchintam/aureproof/issues/34)); the historical mock result predates the label migration.
- [ ] **Run the authorized, budgeted live Claude Code episode** to finish spike check 2 ([#7](https://github.com/bhargavchintam/aureproof/issues/7)) after its listed dependencies. Follow the spike README's private key-file procedure.
- [ ] **Set up PyPI Trusted Publishing and qualify the offline alpha** ([#37](https://github.com/bhargavchintam/aureproof/issues/37), M1).
- [x] **Dependabot PRs** #1–#4 superseded by the grouped #21 (merged); #23 (pydantic 2.14) merged.
