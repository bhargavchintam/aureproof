# Difficulty probe results

Issue #44 (AP-019). Rules: [`specs/thr/README.md`](../../specs/thr/README.md) §6.
Reproduce with `uv run aureproof task probe <task> --json` (Bandit) and
`--model <id>` for the single-shot baseline.

## 2026-10-28: Bandit, the three calibrated pairs

Scoring identity `sha256:512fa1e98bb368ad6f60639518041beed77f982664827b242d3f49114c1616f0`.
Bandit system identity `sha256:08c9dca4bb88da25b0f0124e628403365a1eff31b2a2e53ef7dd107048b45b18`
(`bandit[sarif]==1.9.4`, `-q -r . -f sarif`).

| Task | Task identity | Vulnerable | Repaired | Known-defect recall | Strict yield | Solved |
| --- | --- | --- | --- | --- | --- | --- |
| `authz-001` | `sha256:23f886826ca541c8b2ff99b653672dd565862d4d17e82208a751c2061855f734` | `completed_no_findings` | `completed_no_findings` | 0/1 | 0/0 | no |
| `path-001` | `sha256:0b54ab218d712214a19be228b7621834a1d3e5689baeac5fb7b566acf27d75ce` | `completed_no_findings` | `completed_no_findings` | 0/1 | 0/0 | no |
| `authz-002` | `sha256:d660630cc27ba32d7be67e4dc21573eca68f81718ab1119273485d7dd0e63b57` | `completed_no_findings` | `completed_no_findings` | 0/1 | 0/0 | no |

Bandit reports nothing on any of the six variants. None of the defects has a lexical
signature Bandit's rules know: a missing ownership check, a decode after a name check,
and a lookup not tied to its tenant. Strict yield is 0/0, undefined, because Bandit
submitted no findings.

## Single-shot model: not run yet

The single-shot baseline needs a provider key (#7). Until it runs, every pair's
saturation is `incomplete`, and #47's stop/go cannot treat the probe as done. When it
runs, record the model ID, the config identity printed by `task probe --json`, the
request IDs from each episode note, and any refusals here.
