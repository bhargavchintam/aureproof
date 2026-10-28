<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Agentic Benchmark Checklist: self-assessment

Issue #61. This is a self-assessment against the
[Agentic Benchmark Checklist](https://github.com/uiuc-kang-lab/agentic-benchmarks/blob/main/ABC.md)
(ABC; Zhu et al., [arXiv:2507.02825](https://arxiv.org/abs/2507.02825)), as of
2026-10-28, for the fixture pack at revision `0.1.0-dev` and the v0.1 pipeline. Item
IDs follow the checklist. The descriptions here are short paraphrases, so read the
source for the exact wording. "Met" always points at evidence in this repository.
Several items cannot be met yet, and the reason is given for each.

**Status key:** met · partly met · not met · not applicable (n/a).

## I. Outcome validity

Aureproof grades an agent's `findings.json` with a deterministic matcher against
evaluator-only labels (`specs/scoring/scoring.md`). That is closest to the
checklist's *answer matching* and *substring matching* categories. There is no LLM
judge, no unit or fuzz testing of agent code (v0.1 never executes it, ADR-0004), and
no state matching.

| Item | Paraphrase | Status | Evidence and limits |
| --- | --- | --- | --- |
| I.a.1 | Semantically equivalent answers match | met | A finding matches by location (symbol, or a line range with tolerance) and by any CWE in the defect's accepted set, which covers equivalent classes (scoring.md M1–M3; `fixtures/oracles/*/labels.json`) |
| I.a.2 | Redundant words do not break matching | met | Only the structured fields `cwe` and `locations` are graded; the free-text `description` is never matched |
| I.b.1 | Negation is handled | n/a | No text is matched. A submitted finding asserts a defect by construction |
| I.b.2 | Listing every possible answer does not pay | met | The THR `spray_cheat` control requires strict yield ≤ 0.25 when every symbol is flagged with every accepted CWE (`specs/thr/README.md` §3), and all three pairs pass it. The primary metric, strict confirmed yield, penalizes every extra finding (ADR-0006) |
| I.b.3 | The ground truth resists guessing | met | Each defect needs the right file and symbol (or lines) and an accepted CWE class. Decoys and the repaired variant refute naive guesses (M6, M7) |
| I.c.1, I.c.2 | LLM judge accuracy and robustness | n/a | No LLM judge: grading is a pure function in the controller (ADR-0004) |
| I.d.1, I.d.2 | Unit tests checked and measured | n/a | Agent code is not executed in v0.1. The grader's own tests run at ≥90% coverage in CI, and the golden vectors were written before the matcher (scoring.md §8) |
| I.e.1–I.e.3 | Fuzz testing | n/a | Not used to grade |
| I.f.2, I.f.3 | End-to-end tests exercise the code without flakiness | partly met | Calibration PoCs exercise the labeled defect end to end, and every THR control is re-run for determinism (`aureproof task validate`). Agent-side end-to-end execution is v0.2 |
| I.g.1–I.g.3 | State matching | n/a | Not used |
| I.h.1 | The answer format is in the task description | met | Each `instruction.md` gives the `findings.json` schema and says that false alarms count |
| I.h.2 | Random guessing rarely succeeds | met | See I.b.2 and I.b.3. The `nop` control confirms that an empty answer scores zero recall |
| I.I.1 | Quality metrics resist exploitation | met | Strict yield and scoped false-alarm rate are reported, and recall alone is never headlined. `spray_cheat` is a required control, and any metric that rewards spraying makes the task unhealthy |

## II. Challenge validity (the plan's "task validity")

| Item | Paraphrase | Status | Evidence and limits |
| --- | --- | --- | --- |
| II.1 | Tool versions are specified | met | The system identity pins Inspect, inspect_swe, the Claude Code version, the model, settings, tools and the sandbox image digest (`runners/inspect_runner.py::system_spec`, `runners/compose.yaml`) |
| II.2 | API tools stay accessible | met (by design) | No external API tool is offered: the sandbox has no network, and hosted tools are withheld (`docs/bridge-coverage.md`, T-ELEV-1/2) |
| II.3 | Errors from unavailable services are handled | met | An infrastructure failure is `infra_failure`, a recorded new attempt. A configuration fault fails preflight before dispatch (`docs/fault-qualification.md`) |
| II.4 | State is cleared between runs | met | Each attempt is a fresh Docker sandbox holding only one variant's files |
| II.5 | The agent is isolated from the ground truth | met | Labels live in a separate evaluator-only tree that is never mounted. An evaluator-only canary is checked in agent views and in run logs (`tests/integration/test_bridge_qualification.py`, T-INFO-1) |
| II.6 | Annotated ground truth is verified | partly met | Labels are AST-checked against the code, and calibration PoCs demonstrate each defect. **The independent reviewer has not signed off yet (#31).** The THRs are unreviewed and unfrozen |
| II.7 | Each task is solvable | met | The `reference_positive` control and the calibration PoC show that the labeled defect exists and can be credited |
| II.8 | An oracle solver solves all challenges | met | `reference_positive` submits the labeled finding and is credited on every pair; `aureproof task validate` gives HEALTHY for all three |
| II.9 | No shortcut passes without doing the task | met | The verdict is computed in the controller from captured bytes, and planted `verdict.json` or `reward.txt` files are ignored (T-TAMP-1). Spraying fails `spray_cheat` |

## III. Benchmark reporting

| Item | Paraphrase | Status | Evidence and limits |
| --- | --- | --- | --- |
| III.1 | Open source | met | Apache-2.0 code and CC-BY-4.0 fixtures in a public repository |
| III.2 | Open evaluation harness | met | `aureproof` CLI: `run`, `score --offline`, `compare`, `adjudicate`, `task validate`, `task probe` |
| III.3 | Contamination safeguards | partly met | Canaries in every file; public tasks are development-only; a private assessment split is planned (`docs/contamination.md`). **The private split holds no tasks yet** |
| III.4 | The dataset is updated over time | partly met | Revisions are versioned, and the pack grows to about 20 cases (#49, after the M2 go). There is no refresh cadence yet |
| III.5 | Measured constructs are tied to target capabilities | met | `fixtures/DATASET_CARD.md` and `docs/scope.md`: precision-first discovery of synthetic defects, a controlled skill and not real-world capability |
| III.6 | What is evaluated is stated | met | Every result is bound to a SystemSpec identity (subject, scaffold, model, tools, settings). Model and scaffold are evaluated together |
| III.7 | Flaws are prevented, found and corrected | met | THR controls, adjudication with recorded label changes and new revisions (`specs/adjudication`), the STRIDE matrix and the fault matrix |
| III.8 | The impact of unavoidable flaws is discussed | partly met | Known limits are in each oracle README, the dataset card and `docs/bridge-coverage.md`. One open spec conflict is recorded in `docs/fault-qualification.md` |
| III.9 | The impact of flaws is quantified | partly met | Unresolved, invalid, refusal, infrastructure-failure and evidence-incomplete rates carry exact denominators. **No assessment has run yet (#54)**, so there are no measured values |
| III.10 | Statistical significance is reported | met | Exact sign-flip p-value, a test-inversion CI and Wilson intervals, with at least 6 clusters for any decisive outcome (`specs/decision`, `aureproof compare`) |
| III.11 | Results are interpreted in light of flaws | met | Three-way gate: low power, unresolved findings or a mismatch never become a pass. Reports state that the uncertainty is not a population claim (`docs/guides/gate-action.md`) |
| III.12 | Non-AI baselines are reported | partly met | Bandit (a static analyzer) is the non-AI baseline and solves none of the three pairs (`docs/research/difficulty-probe.md`). **There is no human-expert baseline** |
| III.13 | A trivial-agent baseline is reported | met | The `nop` control (an empty submission, recall 0) and the single-shot model probe. The latter is built, and its live run waits for a key (#7) |

## Open items that block a fuller self-assessment

- Independent label review and frozen THRs (#31).
- A populated private assessment split, and an assessment run with measured flaw rates
  (#52, #54).
- A human-expert baseline. It is not planned for v0.1, and this document says so.
- The **BetterBench assessment request** is outward-facing and goes through
  BetterBench's own process. It has **not been submitted**. The maintainer submits it,
  and its status will be recorded here.
