<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Contracts: JSON Schemas (v0.1)

JSON Schema 2020-12 files for the records defined in
[`../scoring/scoring.md`](../scoring/scoring.md) and plan v2 §3.5–§3.7. They are
**generated** from the Pydantic models in
[`src/aureproof/contracts/`](../../src/aureproof/contracts/). Don't edit them by
hand:

```bash
uv run python scripts/export_schemas.py           # regenerate
uv run python scripts/export_schemas.py --check   # CI-style drift check
```

| Schema | Record |
| --- | --- |
| `finding.schema.json` | One agent finding (§2.1; shape rules N1–N4) |
| `findings-file.schema.json` | The `findings.json` array an agent writes |
| `label-set.schema.json` | Evaluator-only defect labels (§2.2) |
| `verdict-record.schema.json` | One finding verdict with its rule (§4.4) |
| `episode-signals.schema.json` | Controller-observed episode facts (§5.1) |
| `metric-record.schema.json` | A metric with its numerator and denominator (§6) |
| `event.schema.json` | An evidence event with its `observation_source` trust tier |
| `submission.schema.json` | Captured submission by digest (`findings`, or `poc_ref`, never executed in v0.1) |

**Schemas are necessary, not sufficient.** The models also enforce two rules
that JSON Schema can't express: `end_line ≥ start_line`, and rejecting
integral floats such as `862.0`. Checks that need the agent view (the file
exists; the lines are within it) belong to the matcher. Conformance vectors:
[`conformance/contracts/v0.1/`](../../conformance/contracts/v0.1/).

SARIF 2.1.0 mapping: `aureproof.contracts.sarif` (export is lossless; import
recovers CWEs from `ruleId`, CWE `taxa`, or rule tags such as
`external/cwe/cwe-089`).
