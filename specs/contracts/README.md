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
| `task-spec.schema.json` | A task by content: revisions, agent views (file digests), evaluator-only label reference, cluster, canary, budget |
| `system-spec.schema.json` | Everything that can change agent behavior: subject, interface mode, hosted tools, models with explicit provider identity, prompts, tools, settings, runner, telemetry, budget |
| `episode-spec.schema.json` | Task × variant × system × protocol × repetition, with an `episode_id` derived from those bindings |
| `attempt-record.schema.json` | One runner dispatch owned by Aureproof (ADR-0003) |

**Identities are content-derived** (issue #10). `TaskSpec.identity` and `SystemSpec.identity` are the
`sha256:` digests of the record's RFC 8785 canonical JSON. Any change to a revision, a file, a
model, a prompt, a tool, a setting, the runner or the budget therefore produces a new identity.
Provider identity fields are required and nullable: `null` records *not returned by the provider*,
instead of silently omitting the field. `episode_id` is derived from its bindings, and `attempt_id` is
`<episode_id>/a<n>`, so both are fixed before dispatch and checked when a record is loaded.

**Schemas are necessary, not sufficient.** The models also enforce two rules
that JSON Schema can't express: `end_line ≥ start_line`, and rejecting
integral floats such as `862.0`. Checks that need the agent view (the file
exists; the lines are within it) belong to the matcher. Conformance vectors:
[`conformance/contracts/v0.1/`](../../conformance/contracts/v0.1/).

SARIF 2.1.0 mapping: `aureproof.contracts.sarif` (export is lossless; import
recovers CWEs from `ruleId`, CWE `taxa`, or rule tags such as
`external/cwe/cwe-089`).
