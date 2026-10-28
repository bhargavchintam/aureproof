<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Aureproof

**An open-source integrity layer for AI-agent evaluations.**

> *Every claim, backed by evidence.*

[![CI](https://github.com/bhargavchintam/aureproof/actions/workflows/ci.yml/badge.svg)](https://github.com/bhargavchintam/aureproof/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/bhargavchintam/aureproof/badge)](https://scorecard.dev/viewer/?uri=github.com/bhargavchintam/aureproof)
[![REUSE status](https://api.reuse.software/badge/github.com/bhargavchintam/aureproof)](https://api.reuse.software/info/github.com/bhargavchintam/aureproof)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

> **Status: pre-alpha (0.0.x), under active construction.** No benchmark
> result, isolation guarantee, or performance claim is asserted yet. This
> repository has the foundation, findings/scoring core, and unsigned bundle
> integrity core. M0 remains open and M1 is partially implemented; see the
> [current status and ordered work](docs/project-status.md) and the
> [implementation plan](docs/aureproof-plan-v2.md).

## What it does

<p align="center">
  <img src="docs/media/architecture.svg" alt="An agent evaluation run passes three checks: a task health record that proves the grader works, a signed evidence bundle anyone can verify and re-score offline, and a pre-registered gate that returns pass, fail or inconclusive" width="900">
</p>

On top of the runners teams already use (Inspect AI first; Harbor next),
Aureproof certifies three things about an evaluation:

1. **The instrument** — a per-task **health record** proves the grader works
   (its reference-positive, repaired-negative, no-op, and anti-cheat controls
   pass) *before* a task is allowed to count.
2. **The record** — a **signed, re-scorable evidence bundle**: content-addressed
   artifacts, a hash-chained journal, an in-toto statement, and a Sigstore
   signature. Anyone can verify and re-score it offline.
3. **The decision** — a **pre-registered** pass / fail / **inconclusive**
   regression gate with cluster-aware statistics, so a result that the data
   cannot support is reported as inconclusive rather than as a win.

Its flagship benchmark measures whether a security agent's findings are real —
**false alarms included** — the problem the 2026 "AI slop" wave made concrete.

## Scope and limits

- **In scope (v0.1):** security-defect *discovery* on self-authored synthetic
  Python fixtures; structured findings graded by a deterministic label matcher
  in the trusted controller; offline, signed bundles; an A/B decision gate.
- **Not yet:** executing agent-submitted proof-of-concept code (v0.2), real-CVE
  tasks, patch grading, chat/RAG/voice, multi-agent systems, training.
- **Synthetic fixtures measure controlled skills, not real-world capability.**

## How it compares

Aureproof is designed to **complement** these projects, not replace them, and
to contribute fixes upstream. To our knowledge, the combination below is not
offered as one tool today; see [`docs/plan-review.md`](docs/plan-review.md) for
the cited landscape.

| | Task-health records | Signed, re-scorable results | Pre-registered 3-way decision |
| --- | --- | --- | --- |
| Inspect AI | admission checks | re-score yes, signing no | clustered SE only |
| Harbor / Terminal-Bench | admission checks | regrade yes, signing no | — |
| SEC-bench / CyberGym | — | — | — |
| Every Eval Ever | — | interchange, no signing | — |
| **Aureproof (planned)** | **persistent + exclusion** | **yes** | **yes** |

## Try it offline

Validate, re-score and report a sealed example bundle. No credentials, no network:

```bash
uv sync --frozen
uv run aureproof validate examples/bundles/tutorial-v0.1
uv run aureproof score examples/bundles/tutorial-v0.1 --offline
uv run aureproof report examples/bundles/tutorial-v0.1 --out report.html
```

Walkthrough: [`docs/guides/tutorial.md`](docs/guides/tutorial.md).

Guides: [authoring a task](docs/guides/authoring-tasks.md) (task-health controls, licensing),
[reading results](docs/guides/reading-results.md) (verdicts, denominators, exclusions,
refusals) and [the comparison gate](docs/guides/gate-action.md) (pass, fail, inconclusive).

## Quickstart (development)

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
uv sync                 # create the environment from the locked dependencies
uv run aureproof --version
uv run pytest           # tests + coverage
uv run ruff check .     # lint
uv run mypy             # types
uv run lint-imports     # architecture boundaries (plan v2 §3.2)
```

Install the pre-commit hooks once: `uvx pre-commit install`.

## Documentation

- [`docs/aureproof-plan-v2.md`](docs/aureproof-plan-v2.md) — the full plan (the spec this repo implements)
- [`docs/plan-review.md`](docs/plan-review.md) — the review and verified landscape
- [`docs/scope.md`](docs/scope.md) — personas, goals, non-goals
- [`docs/adr/`](docs/adr/) — architecture decision records
- [`ROADMAP.md`](ROADMAP.md) — milestones M0–M5
- [`docs/project-status.md`](docs/project-status.md) — audited progress, effort assumptions, and execution order

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Commits are signed off under the
[Developer Certificate of Origin](https://developercertificate.org/). By
participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Please
read [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md) before adding fixtures or tasks.

## Security

Report vulnerabilities privately per [`SECURITY.md`](SECURITY.md).

## License

Code is [Apache-2.0](LICENSE). Self-authored fixtures are CC-BY-4.0. The Code of
Conduct is adapted from the Contributor Covenant 3.0 (CC-BY-SA-4.0). The
repository is [REUSE](https://reuse.software/)-compliant; per-file terms are in
each file's SPDX header or in [`REUSE.toml`](REUSE.toml).
