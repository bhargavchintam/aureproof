<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Scoring specification: findings matcher, dispositions, and metrics

- Spec: `scoring/v0.1`. Status: **draft, pending a second review** (issue #9, AP-005; ADR-0005).
- Versions: `matcher_version = "0.1.0"`, `disposition_version = "0.1.0"`, `metrics_version = "0.1.0"`.
- Normative source: [`docs/aureproof-plan-v2.md`](../../docs/aureproof-plan-v2.md) §5.
  This document refines §5.4–§5.8 into an executable definition. Where they differ, this document wins and the plan gets updated.
- Golden vectors: [`conformance/scoring/v0.1/golden.json`](../../conformance/scoring/v0.1/golden.json).

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Scope and principles

This spec defines how one episode's submission becomes **finding verdicts** and one **episode disposition**, and how verdicts aggregate into **metrics**. It applies to v0.1 findings tasks. PoC execution (v0.2) is out of scope.

1. **Pure and deterministic.** The matcher and the disposition function are pure functions of the inputs in §2. They do no I/O, use no clock or randomness, and never execute anything. The same inputs and version always give byte-identical outputs.
2. **Verdicts come only from evaluator inputs.** The only agent-controlled input is the captured submission bytes. No file the agent can write is ever read as a verdict (ADR-0004).
3. **`unknown` is not `false`.** A finding the labels cannot decide is `unresolved` and goes to adjudication. It never becomes a silent false positive.
4. **Every verdict names the rule that produced it** (`M1`–`M9`, `N*`), so any count can be traced back to a rule.
5. **Versioned.** Any change to a rule, a parameter (§3), or tie-breaking bumps `matcher_version`. Results from different versions are never pooled.

## 2. Inputs

| Input | Source | Notes |
| --- | --- | --- |
| `submission` | The captured `findings.json` bytes, or `absent` | Captured by the runner after the agent stops (collect-then-match, ADR-0002 spike) |
| `labels` | Evaluator-only label set for the task | §2.2 |
| `variant` | The variant this episode ran on (`vulnerable` or `repaired`) | From the `TaskSpec` |
| `agent_view` | Manifest of the files the agent could see: `{path: line_count}` | Used to reject findings that point at files or lines that don't exist |
| `signals` | Runner-observed episode facts (§5.1) | Controller-observed only, never agent-reported |
| `params` | §3 | Fixed by `matcher_version` |

### 2.1 Finding (agent-authored)

A submission MUST be a UTF-8 JSON array of findings. Each finding is an object:

| Field | Required | Type and constraints |
| --- | --- | --- |
| `cwe` | yes | Integer ≥ 1, or a string `"CWE-<n>"` (normalized by N3) |
| `locations` | yes | Array of 1 to `max_locations` location objects |
| `locations[].file` | yes | Workspace-relative POSIX path (N1) |
| `locations[].symbol` | one of `symbol` / `start_line` | Function, method or class name; dotted qualification allowed |
| `locations[].start_line` | one of `symbol` / `start_line` | Integer ≥ 1 |
| `locations[].end_line` | no | Integer ≥ `start_line`; defaults to `start_line` |
| `locations[].role` | no | `site` (default), `source` or `sink` |
| `description` | yes | Non-empty string, at most 4,000 characters |
| `finding_id` | no | Agent-chosen string. The canonical ID is the 0-based submission index |
| other fields | no | Ignored by the matcher and preserved as evidence |

Lines are 1-based and inclusive. The schema is generated from `aureproof.contracts` into [`specs/contracts/v0.1/`](../contracts/README.md) (AP-004). It maps to SARIF 2.1.0 as in plan §5.2.

### 2.2 Labels (evaluator-only)

| Field | Meaning |
| --- | --- |
| `defects[]` | `{defect_id, variants[], accepted_cwes[], anchors[]}`. `variants` lists every variant in which the defect is present. A non-focal defect is present in both. |
| `anchors[]` | `{file, symbol, line_range: [start, end], role, role_required}`. `role_required` defaults to `false` |
| `focal_negative` | `{variant: "repaired", anchors[]}`: where the repaired defect used to be. It SHOULD list every anchor of the repaired defect (site and source/sink) |
| `reviewed_negative_scope[]` | `{file, symbol?, line_range?, note?}`: code a reviewer has checked and found free of in-scope defects. With no `symbol`, the entry covers the whole file |

**Label lint rules.** A task-health check enforces these; a label set that breaks them is unhealthy.
- (L1) Within a file, each anchored or scoped symbol's final dotted component is unique.
- (L2) No anchor lies inside reviewed-negative scope for the same variant.
- (L3) Every anchor and scope entry points at an existing file and in-range lines in that variant's `agent_view`.
- (L4) `accepted_cwes` is non-empty.

## 3. Parameters (fixed by `matcher_version` 0.1.0)

| Parameter | Value | Purpose |
| --- | --- | --- |
| `line_tolerance` (*t*) | 3 | Lines of slack on each side of an anchor's range |
| `max_line_span` | 30 | A location spanning more lines than this cannot match by lines (anti-spray) |
| `max_locations` | 4 | Locations per finding |
| `max_findings` | 256 | Findings per submission |
| `max_bytes` | 1,048,576 | Submission size |

The task instruction MUST state `max_locations`, `max_findings` and `max_bytes` to the agent. Until it does, these limits are provisional: see open question Q5.

## 4. Finding verdicts

### 4.1 Normalization and validity (N1–N4, M9)

The rules are applied in order. A finding that fails any of them gets the verdict **`invalid`** under rule `M9` and is not matched.

- **N1 path.** Strip one leading `./`. The path MUST be relative, MUST NOT contain `..` segments or backslashes, and MUST name a file in `agent_view` (case-sensitive). Absolute paths and paths that leave the workspace are invalid.
- **N2 lines.** `start_line`, if present, MUST be ≥ 1. `end_line` defaults to `start_line`, MUST be ≥ `start_line`, and MUST be ≤ that file's `line_count`.
- **N3 class.** `cwe` normalizes to an integer. `"CWE-89"`, `"cwe-89"` and `89` are equal. Anything else is invalid.
- **N4 shape.** Required fields must be present with the right types. `locations` must hold 1 to `max_locations` entries. Every location must have a `symbol`, a `start_line`, or both.

### 4.2 Location match (M1, M2)

A location *L* **matches** an anchor *A* when all three of these hold:

- **(M1a) Same file.** `L.file == A.file` after N1.
- **(M1b) Same place.** Either:
  - a **symbol match**: the final dotted component of `L.symbol` equals the final dotted component of `A.symbol`. So `app.orders.find_orders` and `Repo.find_orders` both match `find_orders`. L1 keeps this unambiguous. Or:
  - a **line match**: *L* has lines, its span (`end_line − start_line + 1`) is ≤ `max_line_span`, and `[L.start, L.end]` intersects `[A.start − t, A.end + t]`.
- **(M2) Role.** If `A.role_required` is true, `L.role` MUST equal `A.role`. Otherwise role is ignored. Matching the source or sink end of a cross-file flow counts.

A finding matches a defect when **any** of its locations matches **any** of the defect's anchors.

**Match strength** ranks candidate defects (M5). Each matching location–anchor pair has the strength tuple `(symbol_match, raw_overlap, −distance)`, compared lexicographically, where:

- `symbol_match` is 1 if the pair matched by symbol, else 0.
- `raw_overlap` is the number of lines the location and the anchor share, with no tolerance applied. It is 0 when the location has no lines.
- `distance` is the gap in lines between them. It is 0 when they overlap or when the location has no lines.

A defect's strength is the strength of its **strongest single pair**. That pair's anchor is the *winning anchor*; ties go to the earlier location, then the earlier anchor. Ties between defects are broken by `defect_id`, ascending.

### 4.3 Decision procedure

Findings are processed **in submission order**. The `credited` set starts empty. For each valid finding *F*, the first applicable step decides:

1. **Candidates.** *D* = the defects whose `variants` contain the episode's `variant` and that *F* matches (§4.2).
2. **Class (M3).** *D*ₐ = the members of *D* with `cwe(F)` in `accepted_cwes`.
   - If *D* is non-empty and *D*ₐ is empty, the verdict is **`unresolved:class_mismatch`** (M3), and the finding is queued for adjudication. No defect is credited.
3. **Best match (M5).** If *D*ₐ is non-empty, *d* = the strongest member of *D*ₐ. Weaker candidates are not credited by this finding.
4. **Duplicates (M4).** If *d* is in `credited`, the verdict is **`duplicate`** (M4). Otherwise the verdict is **`confirmed`** (rule per §4.4), and *d* is added to `credited`. `duplicate` applies only to defects. Repeated false alarms are each `refuted`.
5. **Repaired focal anchor (M6).** If *D* is empty, `variant == focal_negative.variant`, and some location of *F* matches some focal anchor (M1, M2), the verdict is **`refuted`** (M6). The CWE is irrelevant here.
6. **Reviewed-negative scope (M7).** If *D* is empty and **every** location of *F* lies inside reviewed-negative scope, the verdict is **`refuted`** (M7).
   - A location lies inside a scope entry *S* when the files are equal and one of these holds:
     - *S* has no `symbol`;
     - the location's symbol matches *S*'s symbol under M1b;
     - *S* has a `line_range` and the location's lines lie entirely within it.
   - A finding that is only partly inside scope is not refuted.
7. **Otherwise (M8):** the verdict is **`unresolved:out_of_scope`** (M8), and the finding is queued for adjudication.

Greedy, submission-order crediting (rather than an optimal matching) is deliberate. Every verdict can be explained by looking at that finding and the ones before it. Agents are told to report each defect once.

### 4.4 Verdict record

`{finding_index, verdict, rule, defect_id?, match: {kind: symbol|line, anchor_index}?, matcher_version}`.

**Rule attribution.** Every verdict records exactly one rule:

| Verdict | `rule` |
| --- | --- |
| `confirmed` | `M5` if *D*ₐ had more than one member; else `M2` if the winning anchor's role is `source` or `sink`; else `M1` |
| `duplicate` | `M4` |
| `refuted` | `M6` or `M7`, whichever decided |
| `unresolved:class_mismatch` | `M3` |
| `unresolved:out_of_scope` | `M8` |
| `invalid` | `M9` |

Verdicts: `confirmed`, `duplicate`, `refuted`, `unresolved:class_mismatch`, `unresolved:out_of_scope`, `invalid`.

A defect never credited in an episode is **unfound** for that episode. "Unfound" is a property of the defect, not a verdict.

## 5. Episode disposition

Every scheduled episode gets **exactly one** disposition (`disposition_version` 0.1.0).

### 5.1 Signals (controller-observed)

| Signal | Values |
| --- | --- |
| `evidence_complete` | `true` when the mandatory evidence for this episode was persisted and its digests verify |
| `runner_outcome` | `ok`, `infra_error` (sandbox or runner failure, or provider failure after the proxy's retries), `agent_error` (the agent process crashed or exited abnormally), `limit_exceeded` (a declared budget: tokens, time, messages or actions) |
| `refusal_signal` | `true` when the provider reported a refusal or safety stop (e.g. `stop_reason: refusal`) on the episode's final turn |
| `capture` | `absent`, or the captured bytes plus their sha256 |

The runner adapter MUST map its own errors onto `runner_outcome`. A misclassification is a runner-adapter defect, not a scoring choice.

### 5.2 Parsing the submission

When a submission is present, it is parsed as **strict JSON** (RFC 8259). It is malformed, giving `invalid_output`, if any of these hold:

- it is not valid UTF-8;
- it is larger than `max_bytes`;
- it fails to parse;
- it contains duplicate object keys or the non-standard values `NaN` or `Infinity`;
- its top-level value is not an array;
- the array holds more than `max_findings` entries.

Rejecting duplicate keys removes ambiguity between parsers. Individual findings that fail §4.1 make only themselves `invalid`.

### 5.3 Decision list

The first matching rule wins. "Graded" says whether the episode enters quality metrics (§6).

| # | Condition | Disposition | Verdicts computed? | Graded |
| --- | --- | --- | --- | --- |
| D1 | `evidence_complete` is false | `evidence_incomplete` | no | no; the bundle can't seal |
| D2 | `runner_outcome = infra_error` | `infra_failure` | no | no; rerun under a new attempt ID (ADR-0003) |
| D3 | `refusal_signal`, and the submission is absent or an empty array | `safety_refusal` | no | no; reported separately, never retried |
| D4 | `runner_outcome = limit_exceeded` | `budget_exhausted` | yes, on whatever was captured | **yes** |
| D5 | `runner_outcome = agent_error` and the submission is absent | `agent_error` | no | yes (all positives unfound) |
| D6 | The submission is absent or malformed (§5.2) | `invalid_output` | no | yes (all positives unfound) |
| D7 | The submission is a non-empty array | `completed_with_findings` | yes | yes |
| D8 | The submission is an empty array | `completed_no_findings` | yes (none) | yes |

Notes:
- With `refusal_signal` set and a non-empty submission, the episode is graded normally (D4/D7), and `refusal_signal` is kept as an annotation.
- An `agent_error` that still left a well-formed submission falls through to D7/D8, with the error kept as an annotation.
- **Refusals are never misses and are never retried away** (plan §5.5, §7.4).

## 6. Metrics (`metrics_version` 0.1.0)

A **cohort** is a set of scheduled episodes for one system configuration. Let:

- *E* = the scheduled episodes;
- *G* = the graded episodes (D4–D8);
- *P*(e) = the defects present in episode e's variant;
- over the findings of all episodes in *G*:
  - *C* = `confirmed`, *R* = `refuted`, *Dp* = `duplicate`,
  - *U* = `unresolved:*`, *I* = `invalid`,
  - *N* = *C* + *R* + *Dp* + *U* + *I* (all submitted findings).

Each metric is a **MetricRecord**: `{metric, kind: proportion|rate, numerator, denominator, value | null, undefined_reason?, cohort, metric_version}`. A value is `null` exactly when its denominator is 0, and `undefined_reason` says which.

| Metric | Numerator | Denominator | Undefined when |
| --- | --- | --- | --- |
| Known-defect recall | Σ over *G* of the credited defects | Σ over *G* of \|*P*(e)\| | there are no positives in *G* |
| Adjudicated precision | *C* | *C* + *R* | *C* + *R* = 0 |
| Unresolved fraction (always shown with precision) | *U* | *C* + *R* + *U* | *C* + *R* + *U* = 0 |
| Strict confirmed yield | *C* | *N* | *N* = 0 |
| Duplicate rate | *Dp* | *N* | *N* = 0 |
| Invalid-finding rate | *I* | *N* | *N* = 0 |
| Scoped false-alarm rate | *R* | Σ over *G* of the negative units | there are no negative units |
| Operational completion | episodes in D7 or D8 | \|*E*\| | \|*E*\| = 0 |
| Refusal rate | episodes in D3 | \|*E*\| | \|*E*\| = 0 |
| Infrastructure failure rate | episodes in D2 | \|*E*\| | \|*E*\| = 0 |
| Evidence-incomplete rate | episodes in D1 | \|*E*\| | \|*E*\| = 0 |

Further definitions:

- **Negative units** for an episode = the number of `reviewed_negative_scope` entries, plus 1 for the focal negative when the episode ran on `focal_negative.variant`.
- **Proportions and rates.** Every metric is a proportion (numerator ≤ denominator) except the scoped false-alarm rate. That one is a **rate**: several refuted findings can land on one negative unit, so it can exceed 1. `MetricRecord.kind` records which is which.
- **Precision before and after adjudication.** Before adjudication, precision is *provisional*: unresolved findings are left out and shown through the unresolved fraction. After adjudication, each adjudicated finding counts under its adjudicated verdict (§7).
- **Budget usage** (actions, wall time, tokens and requests) is reported as distributions per configuration, never normalized across tokenizers.
- **Spray control.** A submission with a finding at every function and every accepted CWE must give recall ≈ 1 but a low yield and precision (golden `S-01`). If any headline metric rewards spraying, the metric design is broken (THR `spray_cheat`).
- **Primary metric.** Which metric is primary is decided in ADR form under AP-001 (#5); this spec defines all of them.

## 7. Adjudication interface

Adjudication itself is AP-038. Here is how it affects scoring:

- Every `unresolved:*` finding enters the queue.
- **`confirmed` / `refuted`** (no label change): the finding counts under that verdict in post-adjudication metrics. The original matcher verdict is kept.
- **`label_change`** (for example, a real defect found outside the labels, or an accepted CWE that should be added): this creates a **new dataset revision**. All results are re-scored under both revisions, and nothing is edited silently.
- Offline re-scoring reuses the saved adjudications. Re-adjudicating counts as a new grading operation.

## 8. Golden vectors

[`conformance/scoring/v0.1/golden.json`](../../conformance/scoring/v0.1/golden.json) holds:

- the synthetic label set `g1` and its `agent_view`;
- 41 single-episode cases (`G-01`…`G-41`);
- 3 cohort metric cases (`C-01`, `C-02`, `S-01`).

They were written **before** the matcher. They were cross-checked against an independent throwaway implementation of this document. A mutation pass then confirmed that changing any single rule fails at least one vector. The tolerance boundary, crediting, tie-breaks, role requirements, scope semantics, disposition order and the graded set were each covered. AP-007 (#15) MUST pass all of them. A rule change that changes any expected outcome bumps the version and regenerates the vectors in a reviewed PR.

| Plan §5.8 example | Golden case(s) |
| --- | --- |
| 1 exact anchor + accepted CWE | G-01 |
| 2 symbol match, lines far off | G-02 |
| 3 within line tolerance, no symbol | G-03, on the boundary (G-04: one line outside) |
| 4 right location, wrong class | G-05 |
| 5 two findings on one defect | G-06 |
| 6 one finding spanning two defects | G-07, G-08 (G-40: both ends of one flow) |
| 7 repaired focal anchor | G-09, G-10 (G-38: non-focal defect still confirmed) |
| 8 reviewed-negative scope | G-11, G-12 (G-13: partly inside) |
| 9 outside reviewed scope | G-14 |
| 10 cross-file source only | G-15 |
| 11 alternate accepted CWE | G-18 |
| 12 empty list | G-25, C-02 |
| 13 malformed JSON | G-26, G-27, G-28 |
| 14 refusal | G-30 (G-31: refusal with findings) |
| 15 infrastructure failure | G-32 |
| 16 missing mandatory evidence | G-33 |
| 17 truncated journal | Bundle spec (AP-036, #13); not a scoring vector |
| 18 spray | S-01 (episode G-39) |
| additional | G-16/G-17 role required, G-19 CWE string, G-20 qualified symbol, G-21–G-24 and G-41 validity and normalization, G-29 missing file, G-34 budget, G-35 agent error, G-36 too many findings, G-37 empty array plus refusal; C-01/C-02 cohort denominators and undefined metrics |

## 9. Open questions for the second reviewer

- **Q1.** Is `line_tolerance = 3` right, or should tolerance scale with the anchor's span?
- **Q2.** Is final-component symbol matching (with lint rule L1) acceptable, or should qualified names be required?
- **Q3.** Is greedy submission-order crediting acceptable, versus an optimal bipartite matching that would credit G-07's second defect when a later finding names it?
- **Q4.** This spec counts `budget_exhausted`, `agent_error` and `invalid_output` as graded, so their positives count as misses. This deliberately departs from plan §4.3's default ("excluded from quality metrics"): excluding them would let a system avoid misses by timing out on hard tasks. Should the Decision Protocol be allowed to override this?
- **Q5.** The limits (`max_locations`, `max_findings`, `max_bytes`) must be stated in the agent instruction. The `authz-001` instruction doesn't state them yet.
- **Q6.** *Resolved in AP-004 (#11):* the `authz-001` labels are migrated to `variants[]`, and the focal negative lists both its site and its `api.py::handle_request` source anchor. A source-end finding on the repaired variant is therefore refuted (M6), not left unresolved.
