<!--
SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
SPDX-License-Identifier: Apache-2.0
-->
# Fault qualification (v0.1)

Issue #55 (AP-023). Each recovery scenario v0.1 claims, mapped to the tests that
inject the fault. All of them run in the required CI job, except where a row says
"lane". These rows back the release gates for Recovery and Evidence completeness
(plan §14).

| Scenario | What must hold | Tests |
| --- | --- | --- |
| Restart mid-run | Pre-assigned episode and attempt IDs survive; an in-doubt attempt becomes `unknown` and is never merged with a new one; only permitted stages resume | `tests/storage/test_ledger.py::test_restart_preserves_ids_and_recovers_in_doubt_attempts_without_merging`, `::test_any_crash_sequence_keeps_every_invariant` (Hypothesis over crash points), `::test_illegal_transitions_are_rejected_before_writing` |
| Request identity before dispatch | The attempt's request identity is durable before the runner is called | `tests/storage/test_ledger.py::test_ids_are_assigned_and_request_identity_persisted_before_dispatch`, `tests/runners/test_orchestrate.py::test_confirmed_finding_end_to_end` |
| Interrupted upstream call | A runner that raises mid-call leaves an explicit `unknown` outcome with its error class; an infrastructure failure is re-dispatched as a new, recorded attempt; an agent error never is | `tests/runners/test_orchestrate.py::test_redispatch_is_capped_and_runner_exceptions_are_recorded`, `::test_infrastructure_failure_is_redispatched_as_a_new_attempt`, `::test_agent_errors_are_never_retried`, `tests/runners/test_classify.py::test_only_exception_lines_of_a_traceback_classify` |
| Proxy not ready | A connection refused before any model call is `infra:proxy_not_ready`, re-dispatched as a recorded attempt | `tests/runners/test_classify.py::test_errors_split_into_infrastructure_and_agent` |
| Duplicate delivery or finalization | One result per episode: repeated outcomes and finalization are idempotent, and re-delivering a finished episode dispatches nothing | `tests/storage/test_ledger.py::test_finalization_and_outcomes_are_idempotent`, `::test_closing_a_run_gives_every_episode_exactly_one_disposition`, `tests/runners/test_orchestrate.py::test_a_duplicate_delivery_publishes_one_result` |
| Torn journal | A torn final line is recovered explicitly; corruption in the middle fails visibly | `tests/storage/test_ledger.py::test_torn_final_line_is_recovered_explicitly`, `::test_corruption_in_the_middle_fails_visibly`, `tests/bundle/test_bundle.py::test_any_journal_truncation_is_detected` |
| Partial bundle write | A crash while writing leaves no bundle and no temporary directory; a missing, truncated or edited member never validates | `tests/storage/test_faults.py::test_a_crash_while_writing_a_bundle_leaves_nothing_behind`, `::test_a_partially_written_bundle_never_validates`, `tests/bundle/test_bundle.py::test_any_single_byte_change_is_detected` |
| Partial blob write | A torn blob is detected on read and never accepted as the blob | `tests/storage/test_faults.py::test_a_torn_blob_from_an_earlier_crash_is_detected_and_never_reused` |
| Partial or forged signature | Garbage, missing, altered or wrongly signed signatures are rejected; an unverified signature is never `signed` | `tests/signing/test_sigstore.py::test_garbage_or_missing_signatures_are_rejected`, `::test_altered_bytes_and_wrong_identity_are_rejected`, `tests/bundle/test_signature_gate.py::test_a_present_but_unverified_signature_is_only_skipped` |
| Missing mandatory evidence | The builder refuses to seal without the journal, verdicts and metrics, or with a blob reference it does not hold | `tests/bundle/test_bundle.py::test_builder_refuses_missing_mandatory_evidence`, `::test_builder_refuses_unresolved_blob_refs_and_reserved_paths` |

## Open: an `evidence_incomplete` episode in a sealed bundle

Scoring rule D1 (`specs/scoring/scoring.md` §5.3) says an episode whose evidence is
incomplete is `evidence_incomplete`, "the bundle can't seal". The bundle spec says
incomplete evidence is "never sealed as if complete". But `seal_run` seals such an
episode with `completeness: "complete"`. The committed, signed tutorial bundle
(golden cohort C-01) does exactly that: its metrics report
`evidence_incomplete_rate 1/7`.

Resolving this means choosing semantics, so it waits for the reviewer (#31). One
option is to refuse to seal. The other is a third completeness state (for example
`incomplete`) that a gate treats as failing. Either way the bundle schema
changes, and the tutorial must be regenerated and re-signed. Until then, the decision gate
fails closed on its own: `aureproof compare` re-scores every episode, and an
`evidence_incomplete` episode is never graded.

## Deferred

Hostile agent PoC confinement and other faults that need executed agent code are v0.2
(ADR-0004).
