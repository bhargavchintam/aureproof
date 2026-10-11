---
name: aureproof-dev
description: Use when writing or reviewing code in the Aureproof repo — enforces the quality gates, the pure-core/adapters import boundary, the specs-before-code and test-first workflow, DCO-signed Conventional Commits, and responsible-use rules. Trigger for any edit under src/, tests/, specs/, or fixtures/.
---

# Working in the Aureproof repository

Aureproof is an integrity layer for AI-agent evaluations. The authoritative
spec is `docs/aureproof-plan-v2.md`; the review that produced it is
`docs/plan-review.md`. Read the relevant section before changing behavior.

## Non-negotiable invariants (from the plan)

1. **Never read a verdict from a file untrusted code can write.** Grading is a
   pure function in the trusted controller (ADR-0004).
2. **The runner executes one attempt; Aureproof owns attempt identity and
   retries** (ADR-0003).
3. **`unknown` ≠ `false`, and a refusal is its own outcome** (`safety_refusal`),
   never a miss and never retried away.
4. **Specs before code; conformance vectors before claims.** Changes to
   `specs/` or `src/aureproof/scoring/` need maintainer review (CODEOWNERS).
5. **Fixtures are self-authored/authorized, synthetic, carry a canary.** See
   `RESPONSIBLE_USE.md`.

## The gates — run before every commit

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy                 # strict
uv run lint-imports         # architecture boundary
uv run pytest               # test-first; new behavior needs a test
uvx --with charset-normalizer --from reuse reuse lint
```

All must pass. CI additionally runs gitleaks, CodeQL, and Scorecard.

## Architecture boundary (enforced by `lint-imports`)

Pure core = `contracts`, `scoring`, `stats`, `bundle`: **no** imports of the
adapters (`runners`, `importers`, `exporters`, `oracles`), the `cli`, or any
network/process module (`socket`, `subprocess`, `urllib`, `http`, `httpx`,
`requests`). All I/O and side effects live in adapters or the CLI. Adapters are
registered as entry points, not imported by the core.

If you need a new forbidden/allowed edge, change the contract in
`pyproject.toml` `[tool.importlinter]` and say why in the PR.

## Where things go (plan §3.9)

- New contract/schema → `src/aureproof/contracts/` + `specs/<area>/` + `conformance/<area>/`.
- New scoring/matching rule → `src/aureproof/scoring/` (pure, with golden + Hypothesis tests); update `docs/.../scoring.md` and bump `matcher_version`.
- New runner/importer/exporter/oracle → the matching adapter package + an entry point; never import it from the core.
- New CLI subcommand → `src/aureproof/cli/`; escape all agent-authored strings in any HTML output.

## Adding a fixture

Put agent-visible material in `fixtures/security/<task>/` and evaluator-only
labels/calibration PoCs in `fixtures/oracles/<task>/` (never in an agent build
context). Ship a task-health record with all required controls, including
`nop` and `spray_cheat`. A fixture a single-shot model and Bandit both solve
does not discriminate — redesign it (decoy / cross-file / semantic defect).

## Commits

Conventional Commits, signed off for the DCO:

```bash
git commit -s -m "feat(scoring): ..."
```

Keep PRs small and linked to a plan item (AP-0xx). Disclose substantial AI
assistance in the PR; you remain responsible for correctness.
