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

## 2026-10-29: single-shot model, the three calibrated pairs

Model `claude-haiku-4-5-20251001` (Anthropic Messages, run as
`--model anthropic/claude-haiku-4-5-20251001`), single-shot system identity
`sha256:5c8bc29f8f338358a0370d6aebd6680bd511fc6ad5988481cd67fc9e18b7139f`
(max_tokens 8192, provider-default sampling, no retries). One call per variant, run
from the maintainer's workstation. No refusals and no cut-offs.

| Task | Known-defect recall | Strict yield | Vulnerable verdicts | Repaired verdicts | Solved | Saturation |
| --- | --- | --- | --- | --- | --- | --- |
| `authz-001` | 0/1 | 0/3 | `unresolved:class_mismatch` | `refuted`, `invalid` | no | open |
| `path-001` | 1/1 | 1/4 | `confirmed`, `refuted` | `refuted`, `invalid` | yes | partial |
| `authz-002` | 1/1 | 1/4 | `confirmed`, `refuted` | `refuted`, `refuted` | yes | partial |

Request IDs, in table order (vulnerable, then repaired):
`req_011CgW9AkN6S8qsfHkJUSNRQ`, `req_011CgW9Au3z447t5brUa9YYJ`,
`req_011CgW9BDXiwAmb1Qtv85oeU`, `req_011CgW9BUgZ8WmnePwij6rpN`,
`req_011CgW9BnmEniEfXeGC22eFm`, `req_011CgW9C2AtG4ua1JYjYPadX`. Each call used about
2,100–2,450 input and 140–310 output tokens.

An earlier run the same day gave the same recall, yield, solved and saturation on all
three tasks; only the labels on some unmatched findings differed.

**Reading.** No pair is saturated, so none goes back for redesign (§6). The model finds
the defect in `path-001` and `authz-002` in one shot, but three of its four findings on
each pair are false alarms, including on the repaired code. That is the gap a
precision-first metric is meant to measure. On `authz-001` it names the right place
with the wrong weakness class, which the matcher leaves unresolved rather than credits.

A first attempt passed `anthropic/<id>` to the API unchanged and got a 404. The probe now
accepts the model with or without the `anthropic/` prefix, refuses other providers, and
reports provider errors without a traceback.

## 2026-10-29: the three draft pairs (`ssrf-001`, `redirect-001`, `massassign-001`)

Same Bandit and single-shot configurations as above (single-shot system identity
`sha256:5c8bc29f8f338358a0370d6aebd6680bd511fc6ad5988481cd67fc9e18b7139f`). These pairs
are drafts for the M3 pack (#49), at task revision 0.1.0.

| Task | Task identity |
| --- | --- |
| `ssrf-001` | `sha256:1cd96806e1d4d7e95aa1898819a844355c28238e5b1aac15e76e59858064796b` |
| `redirect-001` | `sha256:6f4686140720cac1f2e48d94332e8c5e44fa5d5abef1ec70e12048b054bc1e48` |
| `massassign-001` | `sha256:4e0d392747c4b45faf321104cb56eef66b1db64868257ee13991c2ff772ee902` |

| Task | Bandit recall | Single-shot recall | Single-shot strict yield | Vulnerable verdicts | Repaired verdicts | Solved | Saturation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ssrf-001` | 0/1 | 0/1 | 0/8 | `unresolved:class_mismatch`, `unresolved:class_mismatch`, `refuted`, `refuted` | `refuted`, `refuted`, `invalid`, `refuted` | no | open |
| `redirect-001` | 0/1 | 1/1 | 1/6 | `confirmed`, `invalid`, `unresolved:class_mismatch` | `refuted`, `refuted`, `refuted` | no | open |
| `massassign-001` | 0/1 | 0/1 | 0/6 | `unresolved:class_mismatch`, `unresolved:class_mismatch` | `refuted`, `refuted`, `refuted`, `refuted` | no | open |

Request IDs, in table order (vulnerable, then repaired): `req_011CgXABHxW7Uvzp75fgZDzB`, `req_011CgXABktkModTNBYgLsB7z`, `req_011CgXACDNhaiiiKWLkoyxrC`, `req_011CgXACao46YCoeciouAa5o`, `req_011CgXAD37LZ9gTxzhFqMFZf`, `req_011CgXADHZ13i9wWEoeQzTge`.

**Reading.** No pair is saturated. Bandit reports nothing on any variant. The
single-shot model finds the `redirect-001` defect, with one confirmed finding out of
six. On `ssrf-001` it described the defect but classed it CWE-601 (open redirect),
which is not in the accepted family, and on `massassign-001` it named the right
function with CWE-434 (file upload). The matcher leaves both unresolved for
adjudication rather than crediting them. A separate call, made only to see those CWEs,
is not part of this record.
