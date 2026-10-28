# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Run one episode end to end: ledger, runner, capture, score, finalize (issue #39).

Every attempt is planned, its request identity persisted, dispatched once,
and its outcome journaled with provider calls and the log digest. Only
infrastructure failures are re-dispatched, as new attempts that are never
merged. The captured bytes go to the content-addressed store before scoring,
so the episode can be re-scored offline from the bytes alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from aureproof.bundle.canonical import digest_ref
from aureproof.contracts import Disposition, LabelSet
from aureproof.runners.port import AttemptRequest, AttemptResult, Runner, redispatchable
from aureproof.scoring import EpisodeScore, score_episode
from aureproof.storage.cas import BlobStore
from aureproof.storage.ledger_store import AttemptLedgerStore

MAX_REDISPATCH = 2  # infrastructure re-dispatches after the initial attempt


@dataclass(frozen=True)
class EpisodeRun:
    episode_id: str
    attempts: list[str]
    score: EpisodeScore
    submission: str | None


def run_episode(
    store: AttemptLedgerStore,
    blobs: BlobStore,
    runner: Runner,
    request: AttemptRequest,
    labels: LabelSet,
    agent_view: Mapping[str, int],
    *,
    max_redispatch: int = MAX_REDISPATCH,
) -> EpisodeRun:
    episode_id = store.plan_episode(request.episode)
    attempts: list[str] = []
    result: AttemptResult | None = None
    submission_ref: str | None = None
    while True:
        attempt = store.plan_attempt(episode_id)
        attempts.append(attempt.attempt_id)
        identity = digest_ref(
            {
                "attempt_id": attempt.attempt_id,
                "task": request.task.identity,
                "system": request.system.identity,
                "protocol": request.episode.protocol,
                "variant": request.variant,
            }
        )
        store.dispatch(attempt.attempt_id, identity)  # durable before the runner is called
        try:
            result = runner.run_attempt(
                AttemptRequest(
                    request.episode,
                    attempt.attempt_id,
                    request.task,
                    request.system,
                    request.root,
                    request.variant,
                )
            )
        except Exception as exc:
            store.record_outcome(
                attempt.attempt_id,
                "unknown",
                error_class=f"infra:runner_exception:{type(exc).__name__}",
            )
            result = None
            if len(attempts) <= max_redispatch:
                continue
            break
        submission_ref = blobs.put(result.submission) if result.submission is not None else None
        store.record_outcome(
            attempt.attempt_id,
            result.outcome,
            runner_run_id=result.runner_run_id,
            error_class=result.error_class,
            submission=submission_ref,
            capture=result.capture,
            capture_detail=result.capture_detail,
            log_digest=result.log_digest,
            provider=dict(result.provider) or None,
        )
        if redispatchable(result) and len(attempts) <= max_redispatch:
            continue
        break

    if result is None:
        score = _infra_only(labels, request, agent_view)
        store.finalize(
            episode_id,
            Disposition.INFRA_FAILURE,
            attempt_id=attempts[-1],
            reason="runner raised on every attempt",
        )
        return EpisodeRun(episode_id, attempts, score, None)
    data = blobs.get(submission_ref) if submission_ref else None
    score = score_episode(
        data, result.signals, labels, variant=request.variant, agent_view=agent_view
    )
    reason = result.error_class
    store.finalize(episode_id, score.disposition, attempt_id=attempts[-1], reason=reason)
    return EpisodeRun(episode_id, attempts, score, submission_ref)


def _infra_only(labels: LabelSet, request: AttemptRequest, view: Mapping[str, int]) -> EpisodeScore:
    from aureproof.contracts import EpisodeSignals, RunnerOutcome

    signals = EpisodeSignals(evidence_complete=True, runner_outcome=RunnerOutcome.INFRA_ERROR)
    return score_episode(None, signals, labels, variant=request.variant, agent_view=view)
