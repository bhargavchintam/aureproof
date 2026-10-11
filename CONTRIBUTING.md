<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Contributing to Aureproof

Thank you for your interest. Aureproof is pre-alpha; the design is fixed by
[`docs/aureproof-plan-v2.md`](docs/aureproof-plan-v2.md), and most work is
tracked in the issues and [`ROADMAP.md`](ROADMAP.md).

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Developer Certificate of Origin (DCO)

This project uses the [DCO](https://developercertificate.org/) instead of a CLA.
Every commit must be signed off:

```bash
git commit -s -m "feat: ..."
```

The sign-off line (`Signed-off-by: Your Name <you@example.com>`) certifies that
you wrote the change or have the right to submit it under the project's license.

## Development setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
uv sync                 # environment from the locked dependencies
uvx pre-commit install  # run the gates on every commit
```

## The gates (must pass before a PR merges)

```bash
uv run ruff check . && uv run ruff format --check .   # lint + format
uv run mypy                                           # strict types
uv run lint-imports                                   # architecture boundaries
uv run pytest                                         # tests + coverage
uvx --with charset-normalizer --from reuse reuse lint # license/SPDX headers
```

CI runs the same gates plus secret scanning, CodeQL, and OpenSSF Scorecard.

## Architecture rules (enforced by `lint-imports`)

The pure core — `contracts`, `scoring`, `stats`, `bundle` — must not import the
adapters (`runners`, `importers`, `exporters`, `oracles`), the `cli`, or any
network/process module. Side effects live in adapters and the CLI. See
[`docs/aureproof-plan-v2.md`](docs/aureproof-plan-v2.md) §3.2.

## How we work

- **Test-first.** Write the failing test, then the minimal code (plan §11).
- **Small, focused PRs**, one logical change each, linked to an issue/plan item.
- **Specs before code.** Changes to `specs/` or scoring semantics need a
  maintainer review (see [`CODEOWNERS`](.github/CODEOWNERS)); once the RFC
  process is active (first external spec change), they go through `rfcs/`.
- **Conventional Commits** for messages (`feat:`, `fix:`, `docs:`, `chore:` …).

## Adding a fixture or task

Read [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md). Fixtures must be self-authored
or authorized, synthetic, carry a canary, and ship with a task-health record.
Open a "Fixture / task proposal" issue first.

## AI-assisted contributions

Disclose substantial AI assistance in your PR (the template has a box). You
remain responsible for correctness, licensing, and having run the gates.
Unverifiable AI-generated submissions may be closed — this project exists to
measure exactly that failure mode, so we hold our own inbox to the same bar.
