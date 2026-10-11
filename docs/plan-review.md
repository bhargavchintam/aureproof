# Aureproof: plan review and upgrade path to A-grade (standards-based, unique, OSS-ready)

*Review date: 6 October 2026*

## Context
This reviews the original v1 plan (813 lines; kept private, not part of this repository), an OSS system for reproducible evaluation of security code agents. The review covers four questions:
- Is the plan sound, and is it ready to start?
- How can it be standards-based **and** distinctive?
- How can it be a strong **open-source contribution** that follows relevant **guidelines and policies**?
- What would lift **every graded lens above B+**?

**Method:** a full read of the plan, an architecture-review framework, and six web-verification passes run on 2026-10-06. Every external fact below was checked in those passes; anything still unverified is flagged as a spike check.
1. Harbor source at v0.24.0
2. Cited sources R1–R16
3. Security-benchmark overlap
4. Eval-rigor tooling overlap
5. Standards and provenance
6. OSS contribution paths and policies

**Companion document:** `aureproof-plan-v2.md`, the plan revised with every change below. **Start work from v2.**

---

## 1. Scorecard: today → after the upgrades

| Lens | Now | Target | What moves it most |
|---|---|---|---|
| Measurement thinking | A | **A+** | Pre-registered signed protocol; ABC self-assessment; adjudicator agreement (κ); refusals as their own outcome |
| Architecture | B− | **A** | Grading as a pure function in the controller; three open specs with conformance tests; Inspect-first ports-and-adapters design; signed bundles |
| Sequencing & scope | C | **A−** | Risk-first milestones M0–M5 with kill criteria; P0 cut to the critical path; reuse instead of building |
| Product / market fit | C+ | **A−** | Precision-first positioning tied to the documented 2026 "AI slop" pain; personas; GitHub Action distribution; design partners |
| Execution readiness | C− | **A** | Day-1 checklist; worked example; ADRs; test-first golden bundles; Linux host; named reviewer |
| Uniqueness *(new)* | C | **A−** | "Integrity layer": task-health records + signed eval attestations + pre-registered decisions; runner-neutral; a public benchmark audit |
| Industry-standard alignment *(new)* | D+ | **A** | SARIF, JSON Schema 2020-12, RFC 8785, in-toto/Sigstore, PEP 740, Scorecard, REUSE, CITATION.cff, Croissant, Every Eval Ever |
| OSS contribution readiness *(new)* | D | **A−** | Governance kit; fixture-contribution pipeline; sequenced upstream plan (NeMo Gym #3675, in-toto #575, EEE, Harbor registry) |
| Policy & compliance *(new)* | C− | **A** | Split code/data licences; SECURITY.md + private reporting; RESPONSIBLE_USE.md; provider-terms rules; refusal accounting; canaries; secret scanning |

Target grades are what the **plan** earns once these changes are written in. Each lens in §4 lists the **evidence** that earns the grade in practice.

## 2. Repositioned in one paragraph
> **Aureproof is an open-source integrity layer for AI-agent evaluations.** It certifies three things, on top of the runners teams already use (Inspect first, Harbor next):
> - the **instrument**: per-task health records
> - the **record**: signed, re-scorable evidence bundles
> - the **decision**: pre-registered pass / fail / inconclusive regression gates
>
> Its flagship benchmark measures what the 2026 AI-slop wave showed matters: whether a security agent's findings are real, **false alarms included**.

Tagline unchanged: *Every claim, backed by evidence.*

## 2a. Is it ready, and is it better than existing OSS? (honest verdict)

**Ready?** Ready to *start*: M0–M2 (~20–26 focused days) are concrete and evidence-based. **Not** ready to *commit* to the full v0.1. Five things are still unproven, and only building or talking to users settles them:
1. The Inspect spike: does the bridge work with no network?
2. Fixture difficulty: are the synthetic bugs too easy?
3. Demand: no practitioner has been asked yet.
4. A named second reviewer.
5. A Linux host.

Treat the M2 stop/go as the real commitment point.

**Better than existing OSS?** Not today, and never *overall*.

| | Inspect AI | Harbor / Terminal-Bench | SEC-bench / Pro | CyberGym | Every Eval Ever | **Aureproof (planned)** |
|---|---|---|---|---|---|---|
| Shipped code / users | Mature, widely used | Active, 29 releases in 6 months | NeurIPS 2025; 300 + 344 tasks | 1,507 real vulnerabilities | Coalition, v0.3.0 | **None yet** |
| Task realism / scale | n/a (framework) | Hundreds of tasks | Real CVEs | Real CVEs | n/a | **~20 synthetic cases**: controlled-skill evidence, not real-world capability |
| Task-health records | Admission checks only | Admission checks only | — | — | — | **Planned (THR)** |
| Signed, re-scorable results | Re-score yes, signing no | Regrade yes, signing no | — | — | Interchange, no signing | **Planned** |
| Pre-registered 3-way decisions | Clustered SE only | — | — | — | — | **Planned** |

- **It's designed to complement these projects, not replace them.** It can only become *best in a narrow lane*: evaluation integrity, plus false-alarm-focused discovery.
- **The moat is thin.** NeMo Gym #3675, in-toto #575 and EEE could absorb pieces. That's acceptable, because contributing there is part of the plan, but it means the differentiation comes from execution quality, not from the idea.

**What must be true before you can honestly claim "better in its lane":**
1. The public-benchmark health audit finds task defects that **upstream confirms**.
2. On a real case, the decision gate gives a more defensible answer than threshold gating (e.g. it calls noise "inconclusive" where a threshold calls it a regression).
3. The fixture pack discriminates where Bandit and single-shot baselines don't, and its false-alarm rates are credible to practitioners.
4. One external team adopts it.
5. An independent reproduction succeeds.

**Guard against governance theater.** On Day 1, do only the cheap standards (they're template work measured in hours): LICENSE/REUSE, DCO, Code of Conduct, SECURITY.md, Scorecard, Trusted Publishing, CITATION.cff. Turn on the heavier ones when a real user or contributor needs them:
- RFC process and maintainer ladder → when the first external contributor appears
- Croissant and EEE exporters → at M4
- OTel export → on request

**Move demand validation to M0.** Before writing code, show a one-page positioning and a mock report to 3–5 practitioners.

**Keep from the original plan:**
- separate grading
- unknown ≠ false
- scoped negatives
- per-attempt identity
- the observation vs enforcement split
- the four reproduction operations
- CLI-first

---

## 3. Critical fixes (prerequisites; nothing above C without these)

| # | Problem | Fix |
|---|---|---|
| C1 | The v0.1 oracle contradicts itself. Findings aren't executable, yet Phase 2/AP-013 build hostile-submission execution. Harbor rewards are forgeable by the agent (#2551) and by executed PoCs (#1779) | v0.1 oracle = **deterministic label matcher, a pure function in the trusted controller**. Evaluator-authored calibration PoCs prove each label. Agent PoCs are stored, not executed, until v0.2. Never read a verdict from a file untrusted code can write |
| C2 | Matching rules are the real measurement and are undefined | `scoring.md`: location tolerance, source vs sink, accepted-CWE sets, duplicates, one→many, partial, repaired-anchor. ≥15 golden examples; versioned `matcher_version`; property tests; SARIF-mappable findings |
| C3 | No adjudication workflow | Adjudication record (reviewer, rationale, time) + `aureproof adjudicate` + a dataset-version bump rule |
| C4 | Ceiling effect: textbook CWEs are solved by every agent and by Bandit | Decoys, cross-file flows, semantic defects (authz); a **difficulty probe** in each health record; canary GUIDs; private assessment split |
| C5 | The A/B is underpowered (≤12 clusters, 8 positives) | **Exact** paired sign-flip permutation over clusters (2^k enumerable), per-cluster tables, Wilson intervals, non-inferiority gate. Demo = sanity contrast (decisive) + close contrast (likely inconclusive) |
| C6 | Harbor binding breaks the evidence invariants: retries delete attempts; real keys go into the sandbox (no proxy, #159); telemetry is on by default; trial files are rewritten after the hook | **Inspect for v0.1** (its bridge isolates keys and withholds hosted tools). **Invert ADR-003:** the runner executes single attempts and Aureproof owns retries. Harbor in v0.2 with `environment_mode="separate"`, `HARBOR_TELEMETRY=off`, and verdicts computed in-process |

---

## 4. Path to A, lens by lens (changes → evidence)

### 4.1 Measurement thinking: A → A+
**Changes**
- **Pre-registration:** the protocol YAML (estimand, cohort, health-record-based exclusions, margin, test, stopping rule) is hashed and **Sigstore-signed before the first assessment episode**.
- The minimum detectable effect from the pilot is written into the protocol. If it's too large, the claim becomes descriptive only.
- **Adjudicator calibration:** two reviewers on ≥20% of unresolved cases, with Cohen's κ reported. Disagreements produce a new dataset version.
- **`safety_refusal` is a distinct outcome.** Provider cyber safeguards can refuse legitimate work (OpenAI documents this), so refusals must never be counted as misses or retried away.
- **Terminal-Bench-style anti-cheat controls per task:** the oracle passes, a no-op (nop) fails, and a deliberate cheater (`/cheat`) fails.
- Publish an **ABC self-assessment** (Task Validity / Outcome Validity / Benchmark Reporting; ABC already includes a CVE-Bench case) and request a **BetterBench** assessment (46 practices, public site).

**Evidence:** the signed protocol's timestamp precedes the assessment logs; `docs/ABC.md`; κ in the report; a BetterBench listing.

### 4.2 Architecture: B− → A
**Changes**
- **Ports and adapters.**
  - The core (`contracts`, `scoring`, `stats`, `bundle`) has no I/O and no network; an **import-linter** contract in CI enforces this.
  - Adapters are entry-point plugins:
    - `aureproof.runners`: inspect (v0.1), harbor (v0.2)
    - `aureproof.importers`: inspect-log, harbor-job, sarif
    - `aureproof.exporters`: Every Eval Ever, OTel GenAI (opt-in), ATIF (pinned)
- **Three open specs.** Each ships as a Markdown spec + JSON Schema 2020-12 + conformance test vectors + a reference implementation:
  1. **Task Health Record (THR)**
     - Controls: reference-positive, repaired-negative, nop, cheat, malformed, irrelevant-trigger.
     - Per-environment status (Harbor #136 shows an oracle failing on only one backend).
     - Difficulty probe, known limits, `frozen_at`.
  2. **Evidence Bundle**
     - SHA-256 over **RFC 8785** canonical JSON, plus a hash-chained journal; the seal stores the event count and head hash so tail truncation is detectable.
     - The seal is an **in-toto Statement v1** with an Aureproof predicate aligned to in-toto `test-result/v0.1`. Track the proposed `eval-result/v0.1` (PR #575).
     - Signed with **sigstore-python** (4.5.0).
  3. **Decision Protocol**: estimand, cluster definition, exact test, margin, and three-way outcome semantics.
- **Lifecycle:** Aureproof owns `planned → verified → scored → sealed`. Inspect's `.eval` log is the raw execution record, sealed by digest. SQLite is a rebuildable index; the JSONL journal is authoritative.
- **Trust tiers:** `observation_source` is either controller/proxy-observed or agent-reported (ATIF and an external agent's internal tool calls are agent-reported).
- **STRIDE threat model** with a control→test traceability matrix: every claimed control has a test.
- **Compatibility policy:** specs are versioned separately from the package; readers accept N-1; `aureproof migrate`.
- **Hardening:** escape agent strings in HTML reports; hash-locked `uv.lock`; digest-pinned images; SSE streaming capture and per-episode budget caps at the proxy.

**Evidence:**
- The conformance suite passes for the reference implementation and one independent consumer (an EEE exporter round-trip).
- import-linter is green, and the threat matrix is 100% tested.
- A stranger can verify a published bundle's signature.

### 4.3 Sequencing & scope: C → A−
**Changes**
- Risk-first milestones M0–M5 (§5), each with an exit demo, a kill criterion and a re-estimate.
- P0 covers only the critical path; everything else is P1/P2 and explicitly "not v0.1".
- **Reuse:** Inspect bridge (AP-015), mini-swe-agent (AP-016), `inspect_swe` Claude Code (AP-017), Bandit `-f sarif` via `bandit[sarif]` (AP-019).
- **Defer:** AP-013 hostile-PoC confinement, non-finding submission types, disk-exhaustion and cleanup fault tests.
- **Dependency fixes:**
  - AP-004 depends on AP-005.
  - The runner spike moves to Day 2.
  - The agent and protocol are chosen in AP-001.
  - Baselines and stats start early on pair #1 and synthetic records.
  - Pair #1 is drafted in M0.
- Public GitHub milestones and a project board mirror `ROADMAP.md`. Rule: no P0 is added without removing one.

**Evidence:** the board matches the roadmap; the M1 re-estimate is recorded; scope changes are logged in the changelog.

### 4.4 Product / market fit: C+ → A−
**Personas and jobs**
1. **Eval engineers** (labs, AISIs, platform teams): "Is this regression real, and can I defend it?"
2. **Security-agent builders:** "What's my false-alarm rate on code I control?"
3. **Benchmark maintainers:** "Which of my tasks are broken?"

**Documented pain (verified, 2026)**
- curl ended its bug bounty when the share of confirmed reports fell from more than 15% to under 5% (Jan).
- Bugcrowd introduced a policy against AI-generated junk reports ("sloptimism"), with queues up more than 334% (Mar).
- HackerOne's guidance makes report quality the researcher's job whether a human or a tool wrote the first draft (May).
- OpenAI found 59.4% of 138 audited SWE-bench Verified tasks flawed (Feb), then ~30% of SWE-Bench Pro tasks broken, and retracted its recommendation (Jul).
- promptfoo, Braintrust and LangSmith gate on thresholds only; none reports statistical inconclusiveness.

**Distribution: go where users already are**
- PyPI.
- A **GitHub Action** (`aureproof gate`) that posts the decision and a bundle link as a PR comment.
- The **Harbor registry** (`harbor publish --public`) for the fixture benchmark.
- **EEE export**, which reaches Hugging Face `.eval_results/`.
- An `aureproof-nat` evaluator plugin for NVIDIA NAT users.
- A NIM-served open-weight subject in the A/B.

**Validation**
- 3–5 practitioner interviews **in M0, before any code**: show a one-page positioning and a mock report.
- 2–3 design partners run the task-health checks or the gate on their own logs before 1.0.

**6-month success metrics:**
- ≥1 external team gating CI
- ≥2 merged upstream PRs
- ≥1 independent reproduction
- ≥5 non-maintainer issues or PRs
- one arXiv report

**Evidence:** anonymized notes in `docs/research/`; a design-partner case study; metrics in the release notes.

### 4.5 Execution readiness: C− → A
**Day-1 checklist**
- [ ] ADR-001…005 record the five decisions: oracle, runner, agent + protocol, goal, reviewer.
- [ ] Worked example (pair #1) with an expected-verdict table for the five Phase-0 scenarios.
- [ ] Bootstrap: uv, ruff, pyright/mypy, pytest + Hypothesis, pre-commit, import-linter, offline CI.
- [ ] OSS kit committed (§4.8).
- [ ] Linux VM provisioned (Docker + nftables). macOS Docker Desktop is unverified for egress enforcement.
- [ ] Second reviewer named, with a review cadence.
- [ ] Golden bundles and expected counts written before the code (test-first).
- [ ] First 15 issues filed, each with definition of done, estimate, dependency and labels.

**Evidence:** fresh clone → `uv sync && pytest` green in under 10 minutes; the offline tutorial runs with no credentials.

### 4.6 Uniqueness *(new)*: C → A−
**What already exists (verified)**
- **Admission-time oracle/nop checks:**
  - Terminal-Bench 3.0 automation: oracle, nop, `/cheat`, canary checks, and a 30-point rubric.
  - Harbor adapters: oracle must hit 100%.
  - SWE-bench `--gold`.
  - NeMo Gym draft #3675.
- **Scattered statistics:** Inspect `stderr(cluster=)`, evalsig, AISI HiBayES.
- **Offline re-scoring:** Inspect, Harbor `regrade`.
- **Interchange:** Every Eval Ever (EvalEval Coalition, v0.3.0), which has **no signing or sealing**.
- **Signed eval results:** essentially none. The in-toto eval-result predicate is only proposed.

**Aureproof's defensible combination**
1. Persistent health records (THR) that drive scoring-time exclusion.
2. Signed, re-scorable eval attestations.
3. Pre-registered three-way decisions.
4. A precision-first security-discovery benchmark: decoys and scoped negatives. SEC-bench Pro reproduces from disclosed reports, and CyberGym is PoC-based.
5. Runner-neutral.

**Proof deliverable:** a **health audit of a public benchmark**, e.g. a small permissively licensed Harbor/Terminal-Bench subset. Publish the findings and file the fixes upstream. It shows uniqueness, rigor and OSS citizenship at once.
**Claims discipline:** no "first" or "gold standard". Use "to our knowledge" plus a cited comparison table.

**Evidence:** the README comparison table with verified links; the audit report plus upstream issues and PRs.

### 4.7 Industry-standard alignment *(new)*: D+ → A
| Concern | Standard (verified version) | Used for | Effort |
|---|---|---|---|
| Findings | **SARIF 2.1.0** + Errata 01 (OASIS); Bandit `-f sarif` via `bandit[sarif]` | Finding import/export, baselines | S |
| Taxonomy | **CWE** | Labels, accepted-CWE sets | S |
| Schemas | **JSON Schema 2020-12** | All three specs | S |
| Digests | **RFC 8785** canonical JSON + SHA-256 | Bundle | S |
| Attestation | **in-toto Statement v1** + DSSE; predicate aligned to `test-result/v0.1`; track PR #575 | Seal | M |
| Signing | **Sigstore** (sigstore-python 4.5.0) | Bundles, pre-registered protocol | S |
| Release provenance | **PyPI Trusted Publishing + PEP 740** (Final; on by default in the PyPA action); `actions/attest` (SLSA v1) | Release CI | S |
| Supply chain | **OpenSSF Scorecard** v5.5.0; target ≥ 8 (pinned dependencies, token permissions, SAST, signed releases, SBOM…) | CI | S |
| Project hygiene | **OpenSSF Best Practices badge** (Passing → Baseline levels) | Repo | S |
| Licensing | **SPDX + REUSE 3.3** (`reuse lint`) | Repo | S |
| SBOM | CycloneDX or SPDX | Releases | S |
| Citation | **CITATION.cff + Zenodo DOI** (don't add `.zenodo.json`; Zenodo would ignore the CFF) | Repo | S |
| Dataset metadata | **Croissant 1.1 + RAI 1.0** (required by the NeurIPS 2026 Evaluations & Datasets track) | Fixture pack | M |
| Eval interchange | **Every Eval Ever 0.3.0** (pre-1.0, so pin it) | Exporter; don't invent an interchange format | M |
| Telemetry | **OTel GenAI semconv** (`invoke_agent`, `execute_tool`; still Development status) | Opt-in exporter only | M |
| Trajectories | **ATIF** v1.7/1.8 (pin `schema_version`) | Import as agent-reported | S |
| Benchmark rigor | **ABC**, **BetterBench** | Self-assessments | S |
| Change mgmt | SemVer, Keep a Changelog, Conventional Commits | Repo | S |

**Evidence:** Scorecard ≥ 8 badge; Best Practices Passing; `reuse lint` green; releases with PEP 740 attestations; the Croissant file validates; the EEE export round-trips.

### 4.8 OSS contribution readiness *(new)*: D → A−
**Inbound: make contributing easy and safe**
- **Kit:**
  - LICENSE (Apache-2.0) + LICENSES/ + NOTICE
  - README (scope and limits)
  - CONTRIBUTING (DCO 1.1 sign-off `-s`, dev setup, **AI-assistance disclosure**)
  - CODE_OF_CONDUCT (**Contributor Covenant 3.0**)
  - SECURITY.md + **GitHub private vulnerability reporting**
  - GOVERNANCE.md (maintainer ladder), MAINTAINERS, CODEOWNERS, SUPPORT.md
  - CITATION.cff, CHANGELOG
  - issue/PR templates
  - RESPONSIBLE_USE.md
- An **RFC process** for spec changes (`rfcs/NNNN-*.md`, the pattern Harbor uses).
- **Fixture contribution kit:**
  - a template
  - CI running `aureproof task validate`: oracle, repaired-negative, nop, cheat, canary present, authorship/licence attestation
  - a reviewer rubric modeled on Terminal-Bench's REVIEWING.md
- Labels: `good first issue`, `help wanted`, `spec`, `adapter`, `fixture`; ≥10 good-first issues at v0.1.0.
- Docs site: tutorial, adapter guide, task-authoring guide, interpretation guide, ADRs.

**Outbound: sequenced upstream plan**
1. **NeMo Gym #3675** (draft: oracle agent + `gym dataset validate`). Coordinate with its author and contribute on top of it (nop/cheat checks, THR export) rather than opening a competing PR. DCO sign-off on every commit.
2. **in-toto attestation #575** (eval-result predicate): bring Aureproof's field requirements.
3. **Every Eval Ever:** propose optional task-health and decision fields; ship the exporter.
4. **Harbor:**
   - Publish the fixture pack to the registry (`--public`) after it passes the oracle and nop checks.
   - Contribute task-health metadata, using #136 as the motivating case.
   - Offer regression tests for the known reward-forging issues (#2551/#1779) through normal issue channels.
5. **inspect_evals Register:** only after an arXiv report exists. The Register needs a paper URL, a 40-character pinned SHA, and logs from two models. Inspect_evals no longer accepts new eval code PRs.

**Evidence:** ≥2 merged upstream PRs; ≥3 external contributors; Best Practices badge; issue-response stats.

### 4.9 Policy & compliance *(new)*: C− → A
| Area | Rule |
|---|---|
| Licensing | Code Apache-2.0; self-authored fixtures CC-BY-4.0 (or CDLA-Permissive-2.0). Never redistribute third-party data without terms: the CyberGym dataset has **no licence tag**, ToolSandbox has a custom Apple licence, SEC-bench is MIT (attribute it). Run a dependency licence scan |
| Authorization | Anthropic's AUP bars discovering or exploiting vulnerabilities "without authorization". Use only self-authored or explicitly authorized targets, egress-blocked sandboxes, and no fixtures that point at third-party live systems. State this in RESPONSIBLE_USE.md |
| Provider terms | Anthropic and OpenAI forbid using outputs to build competing models, so the dataset card must say **"evaluation only; not for training"** and include canaries. OpenAI's no-name/logo clause means no logos and no implied endorsement; name models factually only. Don't retry to bypass safeguards (OpenAI §3.3); record `safety_refusal`. The content of OpenAI's Sharing & Publication Policy is unverified, so read it before the first public results |
| Security | SECURITY.md + private reporting, with a coordinated-disclosure timeline. If an agent surfaces a real vulnerability in third-party code (v0.2+), report it privately to that maintainer and don't publish until it's fixed |
| Dual use | v0.1 is synthetic-only. In v0.2, real-CVE PoCs come only from already-public upstream benchmarks and live in restricted bundles. Public reports summarize; they don't ship working exploits for unpatched issues. Check GitHub's Acceptable Use Policies on exploit content (dual-use research is allowed; content supporting active attacks is not) |
| Data ethics | Canary GUIDs; held-out assessment split; Croissant RAI fields; no personal data |
| Secrets and privacy | Secret scanning (e.g. gitleaks) in CI plus a redaction check on bundles; `HARBOR_TELEMETRY=off`; separate public-redacted and private-full bundles |
| Naming | PyPI/GitHub/domain/trademark check before the public launch; no "gold standard" claims |
| AI-assisted PRs | A disclosure line in the PR template, with maintainer verification (fitting, given the AI-slop context) |

**Evidence:** RESPONSIBLE_USE.md, SECURITY.md, a dataset card with RAI fields, the CI secret scan, and the refusal outcome in the schema.

---

## 5. Milestone roadmap (focused days, cumulative)
| Milestone | Days | Scope | Exit demo | Kill / pivot |
|---|---|---|---|---|
| **M0 Foundations** | 5–6 | **3–5 practitioner interviews (one-page positioning + mock report)**; ADR-001…005; cheap OSS kit; CI (Scorecard, REUSE, pinned actions, secret scan); worked example; Inspect spike; namespace check; Linux VM | Interview notes; fresh clone green; spike verdict | If interviews show no pull for task health or gating: narrow to the benchmark + report. If the bridge can't isolate keys: plain-Docker runner + own proxy |
| **M1 Offline integrity core** | 12–16 | Draft specs (THR, Bundle, Decision) + schemas + conformance vectors; matcher + metrics; RFC 8785 digests, hash chain, in-toto seal; CLI `validate/score/report`; 0.1.0a1 via Trusted Publishing | Phase-1 gate: 9-case golden bundle with exact counts, offline | If counts disagree with the independent calculation: stop, fix the spec |
| **M2 Calibrated slice** | 20–26 | 3 pairs with THR controls; difficulty probe; live episode with mini-swe-agent via the Inspect bridge; Sigstore-signed bundle; offline re-score | §21 vertical slice; **stop/go** | If baselines saturate: redesign fixtures. If there's no isolated oracle: no live expansion |
| **M3 Benchmark + gate** | 30–38 | ~20 cases with reviewer, adjudication, canaries, private split; Claude Code via `inspect_swe`; exact paired gate + GitHub Action; pilot; **signed pre-registered protocol** | Signed protocol + pilot report | If the pilot's detectable effect is too large: descriptive claim only |
| **M4 v0.1.0 release** | 36–46 | Assessment (sanity + close contrasts); report; ABC self-assessment; docs; Croissant card; EEE exporter; SBOM + PEP 740 + DOI; external reproduction | v0.1.0 tag; reproduction | If reproduction fails: no release |
| **M5 Upstream & audit** (overlaps M3+) | +5–8 | NeMo Gym #3675; in-toto #575; Harbor registry; public benchmark audit; arXiv report → inspect_evals Register | ≥2 upstream PRs | — |

**Effort:**
- **~40–55 focused days** in total.
- For comparison, the plan claims 25–40 and its backlog as written is ~50–70.
- Standards and OSS hygiene add ~4–6 days, mostly one-time setup; the reuse substitutions save more than that.

## 6. First 12 days
| Day | Work | Exit artifact |
|---|---|---|
| 1 | uv repo + CI + OSS kit; `scope.md` (personas, goals, non-goals); namespace check; draft pair #1 + labels + calibration PoC | Repo + worked example |
| 2 | **Inspect spike**: bridge under `network_mode: none`; mini-swe-agent / Claude Code writes `findings.json`; scorer runs in the controller; uv-pinnable | ADR-002/003 |
| 3 | `scoring.md` + golden table; THR outline; STRIDE threat model; `protocol-v0.yaml` | Frozen semantics |
| 4 | Pydantic contracts + JSON Schema 2020-12 + conformance vectors (findings only, SARIF mapping) | Schemas |
| 5 | Matcher + metrics, test-first, with Hypothesis invariants | Exact counts |
| 6 | RFC 8785 digests, content-addressed blobs, hash chain, in-toto seal (signing on Day 11) | Integrity tests |
| 7 | CLI `validate/score --offline/report` (escaped HTML); 0.1.0a1 via Trusted Publishing | **Phase-1 gate** |
| 8 | THR controls for pair #1: oracle, repaired-negative, nop, cheat, malformed, irrelevant trigger | First THR |
| 9 | Bandit SARIF importer + single-shot model baseline = difficulty probe | Baselines |
| 10–12 | Live episode via the Inspect bridge → `.eval` log → Sigstore-signed bundle → offline re-score | **Vertical slice / stop-go** |

## 7. Citation and fact corrections for the plan (verified)
| Ref | Correction |
|---|---|
| R9 | Retitle to "Why SWE-bench Verified no longer measures frontier coding capabilities" (Feb 23 2026). Add the Jul 8 2026 "Separating signal from noise" post (~30% of SWE-Bench Pro tasks broken; Pro recommendation retracted) |
| R8 | SEC-bench: MIT; `poc-repo/desc/san` modes + patching; >200 GB disk. SEC-bench Pro: MIT, 344 cases, **PoC reproduction from disclosed reports**, no patching or info modes, needs KVM. Soften §11's claim that discovery is "covered" |
| CyberGym | Levels L0–L3; code Apache-2.0, **dataset has no licence tag**; ~240 GB, ~10 TB with images; a 10-task subset exists |
| R10 Harbor | Separate mode is real (`environment_mode="separate"`). Artifact manifest has no hashes; a collection failure doesn't fail the trial. Retries delete attempts. Telemetry is on by default. 29 releases Apr→Oct 2026 with breaking changes |
| R11–R13 | Attribute the hosted-tool bypass to Inspect's agent-bridge and sandboxing pages; the bridge withholds those tools by default |
| R15 | NAT URL moved to `/latest/improve-workflows/evaluate.html` (pin 1.8). `BaseEvaluator.evaluate_item` / `AtifBaseEvaluator` exist |
| R1 | The link is τ²/τ³-bench (`tau2-bench`); relabel |
| ATIF | An "Active" RFC: v1.8 spec, v1.7 emitted. Not stable; pin it |
| inspect_evals | No longer takes new eval code; use the Register (needs an arXiv paper) |
| R14 Bandit | 1.9.4 (Feb 2026); SARIF output via the `bandit[sarif]` extra |

## 8. Still unverified (resolve in spikes)
- Inspect bridge under `network_mode: none`.
- Docker Desktop on macOS with nftables egress rules.
- `inspect_harbor` maturity.
- Whether EEE can hold THR and decision fields.
- The content of OpenAI's Sharing & Publication Policy.
- Whether the provider-terms rules hold for any additional providers (e.g. NVIDIA NIM terms).

## 9. Outline of `aureproof-plan-v2.md`
1. Positioning, personas, goals, non-goals, success metrics
2. Principles kept from v1
3. Architecture: ports and adapters, trust boundaries, Inspect-first, lifecycle and trust tiers
4. The three open specs (THR, Evidence Bundle, Decision Protocol), with summaries and spec-file stubs to write
5. Oracle and scoring semantics: matcher, matching rules, adjudication
6. Statistics and pre-registered decision protocol
7. Threat model, security, responsible-use and provider-terms policy
8. Standards adoption map
9. OSS governance and contribution model, inbound and outbound
10. Roadmap M0–M5 with gates and kill criteria
11. Backlog v2: re-prioritized, new items, a definition of done for each
12. First 12 days
13. Risk register: adds ceiling, refusal skew, Harbor churn, contamination, upstream dependence
14. Release acceptance criteria v2: adds Scorecard ≥ 8, REUSE, signed bundles, ABC, reproduction
15. Corrected references

## Verification of this review
- Every critique cites the plan section (§) or backlog item (AP-xxx) it targets.
- External facts come from six web passes on 2026-10-06, with URLs and issue/PR numbers available to re-check: Harbor #2551, #1779, #159, #136; NeMo Gym #3675; in-toto #575.
