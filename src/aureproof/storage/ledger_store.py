# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""The durable attempt ledger: plan, dispatch, record, finalize, recover (issue #19).

Every call validates the transition against the folded ledger *before*
appending, then appends durably. The journal is the authority; the SQLite
index is a disposable view that ``rebuild_index`` recreates from it.
"""

from __future__ import annotations

import copy
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureproof.bundle.ledger import AttemptState, Ledger, LedgerError, Outcome
from aureproof.contracts.events import Event, ObservationSource
from aureproof.contracts.specs import AttemptRecord, EpisodeSpec
from aureproof.contracts.verdicts import Disposition
from aureproof.storage.journal import Journal


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class AttemptLedgerStore:
    def __init__(self, root: Path, *, clock: Callable[[], str] = utc_now) -> None:
        self.journal = Journal(root / "journal.jsonl")
        self.clock = clock
        self.ledger = Ledger.fold(self.journal.events)

    def _append(
        self,
        *,
        episode_id: str,
        kind: str,
        payload: dict[str, Any],
        attempt_id: str | None = None,
        blob_refs: list[str] | None = None,
        observation_source: ObservationSource = ObservationSource.CONTROLLER_OBSERVED,
    ) -> None:
        probe = Event(
            seq=len(self.journal.events),
            episode_id=episode_id,
            attempt_id=attempt_id,
            actor="aureproof",
            kind=kind,
            observation_source=observation_source,
            payload=payload,
            blob_refs=blob_refs or [],
        )
        copy.deepcopy(self.ledger).apply(probe)  # raises LedgerError before anything is written
        event = self.journal.append(
            episode_id=episode_id,
            kind=kind,
            payload=payload,
            attempt_id=attempt_id,
            blob_refs=blob_refs,
            observation_source=observation_source,
        )
        self.ledger.apply(event)

    # ---- lifecycle ------------------------------------------------------------------------

    def plan_episode(self, spec: EpisodeSpec) -> str:
        existing = self.ledger.episodes.get(spec.episode_id)
        if existing is not None:
            if existing.spec != spec:
                raise LedgerError(f"episode {spec.episode_id} was planned with other bindings")
            return spec.episode_id  # idempotent
        self._append(
            episode_id=spec.episode_id,
            kind="episode_planned",
            payload={"episode": spec.model_dump(mode="json")},
        )
        return spec.episode_id

    def plan_attempt(self, episode_id: str) -> AttemptRecord:
        """Assign the next attempt ID before dispatch."""
        episode = self.ledger.episodes[episode_id]
        index = len(episode.attempts)
        attempt_id = f"{episode_id}/a{index}"
        self._append(
            episode_id=episode_id,
            kind="attempt_planned",
            attempt_id=attempt_id,
            payload={
                "attempt_id": attempt_id,
                "attempt_index": index,
                "reason": "initial" if index == 0 else "infra_retry",
            },
        )
        return self.record(attempt_id)

    def dispatch(self, attempt_id: str, request_identity: str) -> None:
        """Persist the request identity. Call the runner only after this returns."""
        self._append(
            episode_id=attempt_id.rsplit("/", 1)[0],
            kind="attempt_dispatched",
            attempt_id=attempt_id,
            payload={
                "attempt_id": attempt_id,
                "request_identity": request_identity,
                "at": self.clock(),
            },
        )

    def record_tool(
        self,
        attempt_id: str,
        *,
        tool: str,
        input_sha256: str,
        output_sha256: str | None,
        error: str | None,
        source: ObservationSource,
    ) -> None:
        """One tool call of a dispatched attempt, before its outcome (issue #43)."""
        self._append(
            episode_id=attempt_id.rsplit("/", 1)[0],
            kind="tool_observed",
            attempt_id=attempt_id,
            payload={
                "attempt_id": attempt_id,
                "tool": tool,
                "input_sha256": input_sha256,
                "output_sha256": output_sha256,
                "error": error,
            },
            observation_source=source,
        )

    def record_outcome(
        self,
        attempt_id: str,
        outcome: Outcome,
        *,
        runner_run_id: str | None = None,
        error_class: str | None = None,
        submission: str | None = None,
        capture: str | None = None,
        capture_detail: str | None = None,
        log_digest: str | None = None,
        provider: dict[str, Any] | None = None,
    ) -> None:
        episode_id = attempt_id.rsplit("/", 1)[0]
        payload: dict[str, Any] = {
            "attempt_id": attempt_id,
            "outcome": outcome,
            "at": self.clock(),
            "runner_run_id": runner_run_id,
            "error_class": error_class,
            "submission": submission,
            "capture": capture,
            "capture_detail": capture_detail,
            "log_digest": log_digest,
            "provider": provider,
        }
        current = self._attempt_state(attempt_id)
        if current is not None and current.outcome is not None:
            same = current.outcome.model_dump(exclude={"at"}) == {
                k: v for k, v in payload.items() if k != "at"
            }
            if same:
                return  # duplicate delivery: one result
        self._append(
            episode_id=episode_id,
            kind="attempt_outcome",
            attempt_id=attempt_id,
            payload=payload,
            blob_refs=[submission] if submission else None,
        )

    def finalize(
        self,
        episode_id: str,
        disposition: Disposition,
        *,
        attempt_id: str | None,
        reason: str | None = None,
    ) -> None:
        """Exactly one disposition per episode; a repeated identical call is a no-op."""
        final = self.ledger.episodes[episode_id].final
        if final is not None and (final.disposition, final.attempt_id, final.reason) == (
            disposition,
            attempt_id,
            reason,
        ):
            return
        self._append(
            episode_id=episode_id,
            kind="episode_finalized",
            payload={
                "disposition": disposition.value,
                "attempt_id": attempt_id,
                "at": self.clock(),
                "reason": reason,
            },
        )

    def recover(self) -> list[str]:
        """After a restart: every in-doubt attempt gets an explicit ``unknown`` outcome."""
        recovered = []
        for attempt in self.ledger.in_doubt():
            self.record_outcome(attempt.attempt_id, "unknown", error_class="controller_restart")
            recovered.append(attempt.attempt_id)
        return recovered

    def close_run(self, reason: str) -> list[str]:
        """End the run: every scheduled episode gets exactly one disposition.

        In-doubt attempts are recovered first. Episodes still unfinished are
        finalized as ``infra_failure`` with ``reason`` (visible, never dropped).
        Returns the episode IDs closed this way.
        """
        self.recover()
        closed = []
        for episode_id in self.ledger.unfinished():
            attempts = self.ledger.episodes[episode_id].attempts
            last = attempts[-1].attempt_id if attempts else None
            self.finalize(
                episode_id,
                Disposition.INFRA_FAILURE,
                attempt_id=last,
                reason=f"closed unfinished: {reason}",
            )
            closed.append(episode_id)
        return closed

    # ---- views ----------------------------------------------------------------------------

    def _attempt_state(self, attempt_id: str) -> AttemptState | None:
        episode = self.ledger.episodes.get(attempt_id.rsplit("/", 1)[0])
        return (
            next((a for a in episode.attempts if a.attempt_id == attempt_id), None)
            if episode
            else None
        )

    def record(self, attempt_id: str) -> AttemptRecord:
        state = self._attempt_state(attempt_id)
        if state is None:
            raise KeyError(attempt_id)
        out = state.outcome
        return AttemptRecord(
            episode_id=attempt_id.rsplit("/", 1)[0],
            attempt_index=state.index,
            attempt_id=attempt_id,
            reason=state.reason,  # type: ignore[arg-type]
            status=state.status,  # type: ignore[arg-type]
            runner_run_id=out.runner_run_id if out else None,
            started_at=state.dispatched_at,
            ended_at=out.at if out else None,
            error_class=out.error_class if out else None,
        )

    def records(self) -> list[AttemptRecord]:
        return [
            self.record(a.attempt_id) for e in self.ledger.episodes.values() for a in e.attempts
        ]


def rebuild_index(journal_path: Path, db_path: Path) -> dict[str, int]:
    """Recreate the SQLite index from the journal alone. Returns row counts."""
    store = AttemptLedgerStore(journal_path.parent)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as db:
        db.execute(
            "CREATE TABLE episodes (episode_id TEXT PRIMARY KEY, task TEXT, variant TEXT,"
            " system TEXT, protocol TEXT, repetition INTEGER, disposition TEXT)"
        )
        db.execute(
            "CREATE TABLE attempts (attempt_id TEXT PRIMARY KEY, episode_id TEXT,"
            " idx INTEGER, reason TEXT, status TEXT, request_identity TEXT,"
            " outcome TEXT, error_class TEXT)"
        )
        for eid, ep in sorted(store.ledger.episodes.items()):
            s = ep.spec
            db.execute(
                "INSERT INTO episodes VALUES (?,?,?,?,?,?,?)",
                (
                    eid,
                    s.task,
                    s.variant,
                    s.system,
                    s.protocol,
                    s.repetition,
                    ep.final.disposition.value if ep.final else None,
                ),
            )
            for a in ep.attempts:
                db.execute(
                    "INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)",
                    (
                        a.attempt_id,
                        eid,
                        a.index,
                        a.reason,
                        a.status,
                        a.request_identity,
                        a.outcome.outcome if a.outcome else None,
                        a.outcome.error_class if a.outcome else None,
                    ),
                )
        counts = {
            t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("episodes", "attempts")
        }
    return counts
