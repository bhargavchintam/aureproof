<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Offline tutorial: validate, re-score and report a bundle

No credentials, no network, no model calls. It takes about two minutes.

```bash
git clone https://github.com/bhargavchintam/aureproof && cd aureproof
uv sync --frozen
```

## 1. Validate the sealed bundle

```bash
uv run aureproof validate examples/bundles/tutorial-v0.1
```

```text
V1 structure            pass
V2 members              pass
V3 journal              pass
V4 mandatory evidence   pass
V5 signature            skipped
    - unsigned: Sigstore signing arrives in M2
V6 identity             pass
VALID
```

The bundle holds seven scored episodes (golden cohort `C-01`):
- graded episodes with confirmed and refuted findings;
- an empty submission;
- a budget-exhausted episode;
- a refusal;
- an infrastructure failure;
- an episode with incomplete evidence.

V5 reports *skipped*, never *pass*: the bundle is sealed but not yet signed. To check the
seal itself, pass a digest recorded somewhere you trust:

```bash
uv run aureproof validate examples/bundles/tutorial-v0.1 \
  --trusted-seal-digest "sha256:$(shasum -a 256 examples/bundles/tutorial-v0.1/seal.intoto.json | cut -d' ' -f1)"
```

### Verify the signature (optional; needs the `sign` extra)

```bash
uv sync --frozen --extra sign
uv run aureproof validate examples/bundles/tutorial-v0.1 --require-signature
```

The seal was signed by this repository's `sign.yml` workflow on `main`. Verification runs
offline against that identity and the trust root shipped in the pinned `sigstore`
package. V5 then reports `pass`; altered bytes or a different signer fail it.

## 2. Re-score offline

```bash
uv run aureproof score examples/bundles/tutorial-v0.1 --offline
```

```text
re-score: reproduced
  adjudicated_precision        3/4  0.7500
  duplicate_rate               0/4  0.0000
  evidence_incomplete_rate     1/7  0.1429
  infrastructure_failure_rate  1/7  0.1429
  invalid_finding_rate         0/4  0.0000
  known_defect_recall          3/11  0.2727
  operational_completion       3/7  0.4286
  refusal_rate                 1/7  0.1429
  scoped_false_alarm_rate      1/9  0.1111
  strict_confirmed_yield       3/4  0.7500
  unresolved_fraction          0/4  0.0000
```

The verdicts and metrics are recomputed from the saved submissions and labels alone, then
compared byte for byte with the sealed ones. These counts are the **Phase-1 gate**: they
were calculated by hand before the matcher existed (`conformance/scoring/v0.1/golden.json`,
cohort `C-01`), and a CI test keeps them equal. The refusal and the infrastructure failure
are not misses: they are outside recall's denominator and reported as their own rates.

## 3. Write a report

```bash
uv run aureproof report examples/bundles/tutorial-v0.1 --out report.html
```

The report escapes every agent-authored string and ships a Content-Security-Policy that
allows no scripts. It shows every metric with its numerator and denominator, every episode's
disposition, every finding's verdict and rule, and the bundle's limitations.

## 4. Check a task's health (optional)

```bash
uv run aureproof task validate authz-001
```

This runs the fixture's seven task-health controls twice and checks its canaries. The
record stays *unreviewed* until an independent reviewer signs it off.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | A check failed: invalid bundle, re-score mismatch, or not re-scorable (e.g. labels redacted) |
| 2 | Usage or I/O error: missing path, symlink, unsafe path, existing report without `--force` |
