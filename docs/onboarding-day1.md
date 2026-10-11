<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Day-1 checklist (milestone M0)

From [`aureproof-plan-v2.md`](aureproof-plan-v2.md) §12. The repository
foundation is automated and done; the remaining items are human decisions and
GitHub settings only the maintainer can complete.

## Done (in this repository)

- [x] `uv` project; `aureproof` package skeleton (ports-and-adapters, plan §3.9).
- [x] Quality gates: ruff, mypy (strict), pytest + coverage, import-linter contracts.
- [x] OSS kit: LICENSE + REUSE, README, CONTRIBUTING (DCO), Code of Conduct 3.0, SECURITY, RESPONSIBLE_USE, CITATION.cff, CHANGELOG, ROADMAP, CODEOWNERS, issue/PR templates.
- [x] CI with SHA-pinned actions + least-privilege tokens: quality, secret scan, CodeQL, Scorecard; Dependabot.
- [x] ADRs 0001–0005 drafted; spec stubs (`specs/thr`, `specs/bundle`, `specs/decision`).
- [x] `scope.md`.
- [x] Namespace check (2026-10-07): `aureproof` free on PyPI, GitHub, and the .org/.io/.com domains.

## To do (human / account actions)

- [ ] **Name the second reviewer** and record them in `MAINTAINERS.md` (resolves ADR-0005; required by the release and oracle gates).
- [ ] **Set the Code of Conduct enforcement contact** in `CODE_OF_CONDUCT.md` (a dedicated address or form — avoid a personal email in a public repo).
- [ ] **Schedule 3–5 practitioner interviews**; capture notes under `docs/research/` (M0 gate; decides go / narrow).
- [ ] **Provision a Linux host** (Docker + nftables) for isolation work; Docker Desktop on macOS is development-only and unverified for egress enforcement.
- [ ] **Create the GitHub repo** `bhargavchintam/aureproof`, push `main`, and in Settings enable: private vulnerability reporting, Dependabot, CodeQL, and branch protection on `main` (require PR review + the CI check).
- [ ] **Set up PyPI Trusted Publishing** for the release workflow (added in M1) before the first `0.1.0a1` upload.
- [ ] **Run the Day-2 Inspect spike** (plan §3.3) and record the result in ADR-0002/0003.
- [ ] **File the first 15 issues** (below).

## First 15 issues (plan v2 §11)

1. AP-001 — Freeze scope, primary metric, agent + protocol choice (ADR-001/004/005). `P0`
2. AP-032 — Practitioner interviews + one-page positioning + mock report. `P0`
3. AP-034 — Inspect runner spike → ADR-002/003. `P0`
4. AP-010 — Fixture pair #1 (command injection): fixture, labels, calibration PoC, expected-verdict table. `P0`
5. AP-005 — `scoring.md`: matching rules M1–M9, dispositions, metrics, golden table. `P0`
6. AP-003 — Task/System/Episode/Attempt schemas. `P0`
7. AP-004 — Event/Submission/Finding/Verdict schemas + SARIF mapping (depends on AP-005). `P0`
8. AP-035 — Task Health Record spec + schema + conformance vectors. `P0`
9. AP-036 — Evidence Bundle spec: RFC 8785, hash chain, in-toto seal. `P0`
10. AP-037 — Decision Protocol spec + exact permutation gate. `P0`
11. AP-007 — Matcher + metrics (pure, test-first, Hypothesis invariants). `P0`
12. AP-008 — CLI `validate/score/report` (escaped HTML output). `P0`
13. AP-002 — STRIDE threat model + control→test matrix. `P0`
14. AP-041 — RESPONSIBLE_USE provider-terms rules + `safety_refusal` disposition. `P0`
15. AP-009 — Aureproof-owned attempts + journal; restart recovery. `P0`

A ready-to-run `gh issue create` script can be generated from this list on request.
