<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Every Eval Ever export

Issue #59. `aureproof export-eee` turns one sealed run bundle (one system
configuration) into an [Every Eval Ever](https://pypi.org/project/every-eval-ever/)
aggregate record, pinned to **EEE 0.3.0**. The upstream schema
(`src/aureproof/exporters/schemas/eee-0.3.0-eval.schema.json`, MIT, © 2026 EvalEval) is
vendored and verified by its SHA-256,
`c9c6195aec8a9dfa0b2aba4924ac1aa8a184c9d8ca97cee778cb531088e39b48`.

```bash
uv run aureproof export-eee bundles/a --out eee/a.json \
  --organization "My lab" --timestamp "$(date +%s)"
```

## What maps

| Aureproof | EEE |
| --- | --- |
| Every defined metric, with its exact numerator and denominator | One `evaluation_results` entry: `metric_id` `aureproof.<name>`, `score`, and `details.numerator` and `details.denominator` as strings |
| Metric kind (proportion or rate), direction | `metric_kind`, `metric_unit`, `lower_is_better`, `min_score`, `max_score` |
| System spec: model, provider, protocol, runner, subject | `model_info` (`id` as `developer/model`), `eval_library.additional_details` |
| Seal digest, bundle version, scoring identity, system and protocol identities, cohort | `source_metadata.additional_details` |

`aureproof.exporters.eee.from_eee` reads these back. The round-trip test checks that
identities and exact counts survive.

## What does not map (reported on every export)

Per-finding verdicts and dispositions, the attempt journal with its model and tool
observations, Task Health Records and decisions, adjudications, and the seal and
signature. An undefined metric (zero denominator) is left out and named, because
EEE needs a number.

**An EEE record carries no integrity guarantee.** It holds the seal digest as a
reference only. Verify the source bundle with `aureproof validate
--require-signature`; the EEE copy is for interchange.

## Validation

- Unit tests validate the export against the pinned schema and check the round trip
  (`tests/exporters/test_eee.py`).
- The **EEE consumer** CI workflow runs EEE's own validator
  (`uvx --from every-eval-ever==0.3.0 every_eval_ever validate`) on
  `examples/eee`, which `scripts/make_eee_examples.py` exports from the gate
  examples. EEE requires its `data/<benchmark>/<developer>/<model>/<uuid>.json` layout.
