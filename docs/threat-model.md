<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Threat model (v0.1): STRIDE with a control-to-test matrix

- Status: **living document**, issue #17 (AP-002). Normative source: plan v2 §7.1–§7.2.
- Rule: **a control counts only with passing evidence.** `tests/test_threat_model.py`
  fails if a cited test does not exist, or if a row marked *tested (CI)* cites the
  optional Docker lane. A skipped test is never evidence.
- Scope: the offline core (scoring, contracts, bundle) and the no-cost Inspect spike. The
  live runner adapter (AP-012, #39), signing (#46) and the CLI report (#16) don't exist
  yet. Their controls are listed as *pending*, with the issue that delivers each one.

## Trust boundaries

| Zone | Trusted? | Holds |
| --- | --- | --- |
| Controller: Aureproof core + Inspect process | Trusted | Labels, scorer, provider keys (in process memory only), journal writer |
| Agent sandbox: Docker, `network_mode: none` | **Untrusted** | One fixture variant, the agent, its outputs |
| Evidence: bundle files | Integrity-protected, not secret | Sealed records; confidentiality is not claimed |
| Reader/validator | Trusted for its own conclusions | Re-scores offline from sealed bytes |

Docker on its own is **not** claimed to be a hardened boundary for arbitrary hostile
code. Only the tested controls below are claimed. Docker Desktop on macOS is for
development only. Isolation qualification needs the dedicated Linux host (#32).

## Status values

- **tested (CI)**: covered by tests in the required CI job.
- **tested (lane)**: covered only by the optional Inspect + Docker + mockllm lane (`.github/workflows/inspect-lane.yml`). That's real execution, but mocked inference on a GitHub runner, not the qualified host.
- **partial**: part of the control is tested; the rest is pending, as stated.
- **pending**: not implemented or not tested yet. The delivering issue is named.

## v0.1 matrix

| ID | STRIDE | Threat | Control | Status | Evidence (test IDs) | Limitations / pending |
| --- | --- | --- | --- | --- | --- | --- |
| T-SPOOF-1 | Spoofing | Agent output poses as a controller or verifier event | Every event has an `observation_source` trust tier, and only the controller writes `controller_observed` | partial | `tests/contracts/test_labels_verdicts_events.py::test_events_carry_a_trust_tier` | The tier exists in the contract. Enforcing that the adapter tags agent data `agent_reported` is pending in the runner adapter (#39), with a test that injects a fake verifier event |
| T-TAMP-1 | Tampering | Agent plants a reward or verdict file | The verdict is computed in the controller from captured `findings.json` bytes only; no reward or verdict file is ever read | tested (lane) | `tests/integration/test_inspect_runner.py::test_one_attempt_captures_raw_bytes_and_scores_offline`, `tests/integration/test_inspect_spike.py::test_scripted_subject_grades_from_captured_findings_only`, `tests/spike/test_spike_grading.py::test_current_labels_grade_through_the_core` | Lane evidence uses the scripted mockllm subject. The production adapter (#39) captures raw bytes and their digest, and scores only those |
| T-TAMP-2 | Tampering | Bundle edited after sealing | Member digests, hash-chained journal (count and head sealed), canonical bytes, optional trusted seal digest | tested (CI) | `tests/bundle/test_bundle.py::test_any_single_byte_change_is_detected`, `tests/bundle/test_bundle.py::test_any_journal_truncation_is_detected`, `tests/bundle/test_bundle.py::test_conformance_vector`, `tests/bundle/test_bundle.py::test_seal_metadata_needs_the_trusted_digest` | **Unsigned:** an attacker who can rewrite every file can re-seal. Attributable integrity needs signing (#46) or an out-of-band seal digest |
| T-TAMP-3 | Tampering | Results re-scored with different semantics | Golden vectors pin the matcher; versions are recorded with every verdict | partial | `tests/scoring/test_matcher_golden.py::test_golden_case`, `tests/scoring/test_matcher_golden.py::test_versions_and_params_match_the_vectors` | Parameter overrides can still run under the same `matcher_version`. Binding parameters to the version identity is #36 |
| T-REPUD-1 | Repudiation | "Which protocol, system or attempt produced this?" | Content-derived task and system identities; episode and attempt IDs bound before dispatch; signed protocol and bundle (sign.yml workflow identity) | partial | `tests/contracts/test_specs.py::test_any_system_change_yields_a_new_identity`, `tests/contracts/test_specs.py::test_episode_ids_bind_every_input_before_dispatch`, `tests/storage/test_ledger.py::test_restart_preserves_ids_and_recovers_in_doubt_attempts_without_merging`, `tests/storage/test_ledger.py::test_corruption_in_the_middle_fails_visibly` | Signing and offline identity verification are implemented (#46, tests/signing in the "signatures" CI job). Signing the pre-registered protocol before the assessment is #52 |
| T-INFO-1 | Information disclosure | Agent reads the labels | Labels live in a separate build context, never inside an agent view; only the variant's files are mounted; an evaluator-only oracle canary marks every oracle file | partial | `tests/contracts/test_specs.py::test_conformance_vector`, `tests/spike/test_spike_grading.py::test_agent_view_is_the_mounted_workspace`, `tests/test_dataset_registry.py::test_no_oracle_canary_appears_in_any_agent_visible_file` | Agent views are checked for the oracle canary. Scanning live transcripts and workspaces for it is runner-side, pending (#39) |
| T-INFO-2 | Information disclosure | Provider key reaches the sandbox or the logs | Bridge proxy on the container's loopback; no upstream key in the sandbox env; logs scanned for the key | tested (lane) | `tests/integration/test_inspect_spike.py::test_bridge_works_without_network_and_without_provider_env`, `tests/spike/test_spike_grading.py::test_leak_scan_finds_a_planted_secret`, `tests/spike/test_spike_grading.py::test_key_file_must_be_private` | The digest comparison against a real key runs in `live.py --dry-run` (manual), not CI. Live qualification is #42 |
| T-INFO-3 | Information disclosure | Secrets in a published bundle or the repo | gitleaks on every push and PR; bundle redaction check | partial | — (gitleaks CI job) | The bundle secret/redaction check is pending (#46/#56) |
| T-DOS-1 | Denial of service | Hostile `findings.json`: huge, deep, duplicate keys, non-standard numbers | Byte limit before decoding; depth limit by linear scan before parsing; strict JSON | tested (CI) | `tests/scoring/test_limits.py::test_oversized_submission_is_rejected_before_decoding`, `tests/contracts/test_strict_json.py::test_audit_case_deep_submission_below_byte_limit_is_rejected_quickly`, `tests/contracts/test_strict_json.py::test_rejection_cost_is_linear`, `tests/contracts/test_strict_json.py::test_rejections_are_json_input_errors`, `tests/runners/test_collect.py::test_hostile_artifacts_are_rejected_without_unbounded_reads`, `tests/runners/test_collect.py::test_names_cannot_escape_the_workspace` | Collection in the real sandbox (symlink to /dev/zero, 2 MB file, FIFO) is also lane-tested: `tests/integration/test_inspect_runner.py::test_hostile_artifacts_in_the_real_sandbox` |
| T-DOS-2 | Denial of service | Path tricks in findings or bundles (`../`, absolute paths) | Workspace-relative POSIX paths only; agent-view membership; bundle path rules | tested (CI) | `tests/contracts/test_findings.py::test_invalid_locations`, `tests/scoring/test_matcher_golden.py::test_golden_case`, `tests/bundle/test_bundle.py::test_conformance_vector` | — |
| T-DOS-3 | Denial of service | Hostile bundle documents (NaN, unsafe integers, lone surrogates, deep nesting) | Bounded strict I-JSON parsing; failures become check failures, never exceptions | tested (CI) | `tests/contracts/test_strict_json.py::test_never_raises_anything_but_json_input_error`, `tests/bundle/test_bundle.py::test_conformance_vector`, `tests/bundle/test_hardening.py::test_events_reject_values_without_an_rfc8785_form` | — |
| T-DOS-4 | Denial of service | Runaway episode | Time, token and attempt budgets (ADR-0007); exhaustion becomes `budget_exhausted` and is graded | partial | `tests/scoring/test_matcher_golden.py::test_golden_case` | The scoring side is tested (G-34). Runner-side enforcement and its test are pending (#39, #42) |
| T-ELEV-1 | Elevation of privilege | Network egress from the sandbox | `network_mode: none` | tested (lane) | `tests/integration/test_inspect_spike.py::test_bridge_works_without_network_and_without_provider_env` | Verified on GitHub Linux runners and Docker Desktop. Qualification on the dedicated host is pending (#32) |
| T-ELEV-2 | Elevation of privilege | Hosted tools bypass the sandbox | Withheld at the bridge (`closed-world`); Claude Code `disallowed_tools` (ADR-0007) | pending | — | Observed manually in the spike (WebSearch and WebFetch absent from Claude Code's offered tools). An automated test is pending (#42) |
| T-INJ-1 | Injection | Agent HTML or script in the report | Escape every agent-authored string | pending | — | No report yet (#16) |

## v0.2 additions: executed agent PoCs (not in v0.1)

v0.1 never executes agent-submitted code (ADR-0004; `PocRefSubmission.executed` is `false`
by contract, tested by `tests/contracts/test_labels_verdicts_events.py::test_submission_is_a_tagged_union`).
These controls apply only once v0.2 runs agent PoCs (plan §7.2):

| ID | Threat | Control |
| --- | --- | --- |
| T2-1 | A PoC writes the verdict or reward file (Harbor #1779) | Harbor separate verifier, with the verdict computed in-process |
| T2-2 | A PoC escalates or persists | Low-privilege PoC user; kill the process tree before deciding the verdict |
| T2-3 | Missing artifact counted as a pass | A missing PoC artifact is a failure |
| T2-4 | Cross-trial contamination | A fresh restricted target per submission; cross-trial canaries |
