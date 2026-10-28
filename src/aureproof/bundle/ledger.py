# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The attempt ledger: Aureproof-owned lifecycle state, folded from journal events.

Pure (issue #19, plan v2 §3.4, ADR-0003). The journal is the authority; this
module only replays it and rejects illegal transitions:

    episode_planned -> attempt_planned -> attempt_dispatched -> attempt_outcome
                    -> (another attempt, for infrastructure retries) ...
                    -> episode_finalized (exactly once)

``attempt_dispatched`` carries the request identity and must be durable before
the runner is called. Every dispatched attempt ends with one outcome:
``response``, ``terminal_error`` or an explicit ``unknown`` (e.g. after a crash).
Attempts are never merged and never deleted.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from pydantic import ValidationError

from aureproof.contracts._base import Contract, NonEmptyStr, NonNegativeInt
from aureproof.contracts.events import Event
from aureproof.contracts.specs import DigestRef, EpisodeSpec, UtcTimestamp
from aureproof.contracts.verdicts import Disposition

Outcome = Literal["response", "terminal_error", "unknown"]
KINDS = (
    "episode_planned",
    "attempt_planned",
    "attempt_dispatched",
    "attempt_outcome",
    "episode_finalized",
    "journal_recovered",
)


class LedgerError(ValueError):
    """An event that the lifecycle does not allow (the journal must not accept it)."""


class EpisodePlanned(Contract):
    episode: EpisodeSpec


class AttemptPlanned(Contract):
    attempt_id: NonEmptyStr
    attempt_index: NonNegativeInt
    reason: Literal["initial", "infra_retry"]


class AttemptDispatched(Contract):
    attempt_id: NonEmptyStr
    request_identity: DigestRef  # persisted before the runner is called
    at: UtcTimestamp


class AttemptOutcome(Contract):
    attempt_id: NonEmptyStr
    outcome: Outcome
    at: UtcTimestamp
    runner_run_id: NonEmptyStr | None = None
    error_class: NonEmptyStr | None = None
    submission: DigestRef | None = None


class EpisodeFinalized(Contract):
    disposition: Disposition
    attempt_id: NonEmptyStr | None  # the attempt whose evidence was scored, if any
    at: UtcTimestamp
    reason: str | None = None


class JournalRecovered(Contract):
    note: NonEmptyStr


@dataclass
class AttemptState:
    attempt_id: str
    index: int
    reason: str
    request_identity: str | None = None
    dispatched_at: str | None = None
    outcome: AttemptOutcome | None = None

    @property
    def status(self) -> str:
        if self.outcome is not None:
            return {"response": "completed", "terminal_error": "failed", "unknown": "incomplete"}[
                self.outcome.outcome
            ]
        return "dispatched" if self.request_identity else "planned"


@dataclass
class EpisodeState:
    spec: EpisodeSpec
    attempts: list[AttemptState] = field(default_factory=list)
    final: EpisodeFinalized | None = None

    @property
    def open_attempt(self) -> AttemptState | None:
        return next((a for a in self.attempts if a.outcome is None), None)


@dataclass
class Ledger:
    episodes: dict[str, EpisodeState] = field(default_factory=dict)
    recoveries: int = 0

    # ---- folding ------------------------------------------------------------------------

    @classmethod
    def fold(cls, events: Iterable[Event]) -> Ledger:
        ledger = cls()
        for event in events:
            ledger.apply(event)
        return ledger

    def _episode(self, event: Event) -> EpisodeState:
        state = self.episodes.get(event.episode_id)
        if state is None:
            raise LedgerError(f"{event.kind}: unknown episode {event.episode_id}")
        return state

    def _attempt(self, episode: EpisodeState, attempt_id: str) -> AttemptState:
        for attempt in episode.attempts:
            if attempt.attempt_id == attempt_id:
                return attempt
        raise LedgerError(f"unknown attempt {attempt_id}")

    def apply(self, event: Event) -> None:
        if event.kind not in KINDS:
            raise LedgerError(f"unknown lifecycle event kind {event.kind!r}")
        if event.observation_source != "controller_observed":
            raise LedgerError("lifecycle events are controller-observed only")
        try:
            getattr(self, f"_on_{event.kind}")(event)
        except ValidationError as exc:
            raise LedgerError(
                f"{event.kind}: invalid payload ({exc.error_count()} errors)"
            ) from exc

    def _on_journal_recovered(self, event: Event) -> None:
        JournalRecovered.model_validate(event.payload)
        self.recoveries += 1

    def _on_episode_planned(self, event: Event) -> None:
        planned = EpisodePlanned.model_validate(event.payload)
        if planned.episode.episode_id != event.episode_id:
            raise LedgerError("episode_planned: payload and event disagree on the episode")
        if event.episode_id in self.episodes:
            raise LedgerError(f"episode {event.episode_id} planned twice")
        self.episodes[event.episode_id] = EpisodeState(planned.episode)

    def _on_attempt_planned(self, event: Event) -> None:
        episode = self._episode(event)
        planned = AttemptPlanned.model_validate(event.payload)
        if episode.final is not None:
            raise LedgerError("attempt planned after the episode was finalized")
        if episode.open_attempt is not None:
            raise LedgerError("an attempt is still open; record its outcome first")
        if planned.attempt_index != len(episode.attempts):
            raise LedgerError("attempt indexes are consecutive")
        expected = f"{event.episode_id}/a{planned.attempt_index}"
        if planned.attempt_id != expected or event.attempt_id != expected:
            raise LedgerError(f"attempt id must be {expected}")
        if (planned.attempt_index == 0) != (planned.reason == "initial"):
            raise LedgerError("attempt 0 is initial; later attempts are infra retries")
        if planned.attempt_index > 0:
            prior = episode.attempts[-1].outcome
            if prior is None or prior.outcome == "response":
                raise LedgerError("retry only after an infrastructure failure or unknown outcome")
        episode.attempts.append(AttemptState(expected, planned.attempt_index, planned.reason))

    def _on_attempt_dispatched(self, event: Event) -> None:
        episode = self._episode(event)
        dispatched = AttemptDispatched.model_validate(event.payload)
        attempt = self._attempt(episode, dispatched.attempt_id)
        if attempt.request_identity is not None or attempt.outcome is not None:
            raise LedgerError(f"{attempt.attempt_id} dispatched twice")
        attempt.request_identity = dispatched.request_identity
        attempt.dispatched_at = dispatched.at

    def _on_attempt_outcome(self, event: Event) -> None:
        episode = self._episode(event)
        outcome = AttemptOutcome.model_validate(event.payload)
        attempt = self._attempt(episode, outcome.attempt_id)
        if attempt.request_identity is None:
            raise LedgerError(f"{attempt.attempt_id}: outcome before dispatch")
        if attempt.outcome is not None:
            if attempt.outcome == outcome:
                return  # duplicate delivery of the same outcome: counted once
            raise LedgerError(f"{attempt.attempt_id}: a second, different outcome")
        if outcome.outcome == "terminal_error" and outcome.error_class is None:
            raise LedgerError("a terminal error records its error_class")
        attempt.outcome = outcome

    def _on_episode_finalized(self, event: Event) -> None:
        episode = self._episode(event)
        final = EpisodeFinalized.model_validate(event.payload)
        if episode.final is not None:
            if episode.final == final:
                return  # duplicate delivery: one result
            raise LedgerError(f"episode {event.episode_id} already finalized differently")
        if episode.open_attempt is not None:
            raise LedgerError("finalize only after every attempt has an outcome")
        if final.attempt_id is not None:
            self._attempt(episode, final.attempt_id)
        episode.final = final

    # ---- queries ------------------------------------------------------------------------

    def in_doubt(self) -> list[AttemptState]:
        """Dispatched attempts with no recorded outcome (e.g. the controller crashed)."""
        return [
            a
            for e in self.episodes.values()
            for a in e.attempts
            if a.request_identity is not None and a.outcome is None
        ]

    def unfinished(self) -> list[str]:
        return [eid for eid, e in self.episodes.items() if e.final is None]
