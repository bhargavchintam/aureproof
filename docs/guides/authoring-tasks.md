<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Authoring a task

Issue #56 (guide 1 of 3). How to add a fixture pair that earns a healthy Task Health
Record (THR). The three calibrated pairs (`authz-001`, `path-001`, `authz-002`) are
worked examples; read one before you start.

## 1. Design the pair

- **One defect, one focal function.** The vulnerable and repaired variants differ only
  in the function that holds the defect. A test enforces this
  (`tests/oracles/test_pairs.py::test_pair_differs_only_in_the_focal_function`).
- **No lexical signature.** A pattern scanner or a single-shot model should not find it
  by spotting one line. Use cross-file context, validation done in the wrong order, or
  a check that exists but is incomplete. Run `aureproof task probe` (§4) to find out.
- **Decoys.** Add at least two functions that look suspicious but are safe, such as a
  guard in another file, an intentionally public endpoint, or an allowlist lookup. They
  are how precision gets measured.
- **Self-authored and synthetic.** No third-party code, and no real system, host or
  product (`RESPONSIBLE_USE.md`).

## 2. Lay it out

```
fixtures/security/<task>/instruction.md              # what the agent is asked; output format
fixtures/security/<task>/variants/{vulnerable,repaired}/<package>/...
fixtures/oracles/<task>/labels.json                  # evaluator-only
fixtures/oracles/<task>/calibration_poc.py           # evaluator-only
fixtures/oracles/<task>/README.md, expected_verdicts.md
```

Register the task in `fixtures/dataset.json` with a new public `canary` GUID and a new
evaluator-only `oracle_canary`. Put the public canary in every file. Put the oracle
canary in every oracle file and in no agent-visible file. Public tasks go in the
`development` split; assessment tasks are written privately
([`private-assessment.md`](private-assessment.md)).

## 3. Label it

`labels.json` (schema `aureproof.labels/v0.1`) holds:

- each defect's `variants`, its `accepted_cwes` (the family a reviewer would accept),
  and `anchors` for the site and the source or sink, whose `line_range` must equal the
  symbol's real span;
- a `focal_negative` with every anchor of the defect on the repaired variant;
- the `reviewed_negative_scope`, which lists the decoys and the files reviewed as clean,
  each with a note.

Label lint (L1–L4) rejects drift, collisions, and anchors inside reviewed scope.

## 4. Calibrate it

`calibration_poc.py <variant_dir>` prints JSON. It must report `reference_positive`
(the defect fires), `irrelevant_trigger` and `malformed` (neither may fire). Any other
behavior it checks should give the same result on both variants. Then:

```bash
uv run aureproof task validate <task>   # every THR control, twice; exit 0 only if healthy
uv run aureproof task probe <task>      # Bandit (and --model for single-shot): saturation
```

The required controls are `label_lint`, `reference_positive`, `repaired_negative`,
`nop`, `spray_cheat`, `malformed` and `calibration_poc`, plus a determinism re-run.
They are defined in [`specs/thr`](../../specs/thr/README.md). If both probes solve the
task, it does not discriminate between agents: redesign it.

## 5. License, review and freeze

Fixtures are CC-BY-4.0 (`REUSE.toml`). Regenerate the dataset metadata with
`uv run python scripts/make_croissant.py` and update `fixtures/DATASET_CARD.md`. The
independent reviewer checks the labels and calibration and records the task's known
limits (#31). Only then is the THR frozen. Until it is, the task is healthy but
unreviewed.
