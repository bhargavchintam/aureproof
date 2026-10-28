# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Aureproof-owned attempts: durable journal, restart recovery, idempotency (issue #19)."""

from __future__ import annotations

import copy
import sqlite3
from itertools import count
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aureproof.bundle import Member, build_bundle, canonical_json, validate
from aureproof.bundle.ledger import LedgerError
from aureproof.contracts import Disposition, EpisodeSpec
from aureproof.contracts.events import ObservationSource
from aureproof.storage import StorageError
from aureproof.storage.ledger_store import AttemptLedgerStore, rebuild_index

REQ = "sha256:" + "f" * 64


def _clock() -> object:
    ticks = count()
    return lambda: f"2026-10-27T10:00:{next(ticks) % 60:02d}.000000Z"


def _spec(rep: int = 0) -> EpisodeSpec:
    return EpisodeSpec.plan(
        task="sha256:" + "1" * 64,
        variant="vulnerable",
        system="sha256:" + "2" * 64,
        protocol="sha256:" + "3" * 64,
        repetition=rep,
    )


def _store(tmp_path: Path) -> AttemptLedgerStore:
    return AttemptLedgerStore(tmp_path / "run", clock=_clock())  # type: ignore[arg-type]


def test_ids_are_assigned_and_request_identity_persisted_before_dispatch(tmp_path: Path) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    attempt = store.plan_attempt(eid)
    assert attempt.attempt_id == f"{eid}/a0" and attempt.status == "planned"
    store.dispatch(attempt.attempt_id, REQ)
    # The runner is called only now; the dispatch is already durable on disk.
    reopened = AttemptLedgerStore(tmp_path / "run")
    assert reopened.record(attempt.attempt_id).status == "dispatched"
    assert reopened.ledger.in_doubt()[0].request_identity == REQ


def test_restart_preserves_ids_and_recovers_in_doubt_attempts_without_merging(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    first = store.plan_attempt(eid)
    store.dispatch(first.attempt_id, REQ)
    # --- controller crashes here: no outcome recorded ---
    restarted = AttemptLedgerStore(tmp_path / "run", clock=_clock())  # type: ignore[arg-type]
    assert restarted.recover() == [first.attempt_id]
    assert restarted.record(first.attempt_id).status == "incomplete"
    assert restarted.record(first.attempt_id).error_class == "controller_restart"
    retry = restarted.plan_attempt(eid)
    assert retry.attempt_id == f"{eid}/a1" and retry.reason == "infra_retry"
    restarted.dispatch(retry.attempt_id, REQ)
    restarted.record_outcome(retry.attempt_id, "response", runner_run_id="run-2")
    restarted.finalize(eid, Disposition.COMPLETED_WITH_FINDINGS, attempt_id=retry.attempt_id)
    ids = [r.attempt_id for r in restarted.records()]
    assert ids == [f"{eid}/a0", f"{eid}/a1"]  # both kept; nothing merged
    assert restarted.recover() == []


def test_finalization_and_outcomes_are_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    a = store.plan_attempt(eid)
    store.dispatch(a.attempt_id, REQ)
    store.record_outcome(a.attempt_id, "response", runner_run_id="r")
    store.record_outcome(a.attempt_id, "response", runner_run_id="r")  # duplicate delivery
    store.finalize(eid, Disposition.COMPLETED_NO_FINDINGS, attempt_id=a.attempt_id)
    store.finalize(eid, Disposition.COMPLETED_NO_FINDINGS, attempt_id=a.attempt_id)
    kinds = [e.kind for e in store.journal.events]
    assert kinds.count("attempt_outcome") == 1 and kinds.count("episode_finalized") == 1
    with pytest.raises(LedgerError, match="finalized differently"):
        store.finalize(eid, Disposition.INFRA_FAILURE, attempt_id=a.attempt_id)
    with pytest.raises(LedgerError, match="different outcome"):
        store.record_outcome(a.attempt_id, "terminal_error", error_class="x")


@pytest.mark.parametrize(
    "action",
    [
        lambda s, e, a: s.record_outcome(a, "response"),  # outcome before dispatch
        lambda s, e, a: s.finalize(e, Disposition.COMPLETED_NO_FINDINGS, attempt_id=None),  # open
        lambda s, e, a: s.plan_attempt(e),  # second attempt while one is open
    ],
)
def test_illegal_transitions_are_rejected_before_writing(tmp_path: Path, action: object) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    a = store.plan_attempt(eid)
    before = store.journal.raw()
    with pytest.raises(LedgerError):
        action(store, eid, a.attempt_id)  # type: ignore[operator]
    assert store.journal.raw() == before  # nothing appended


def test_retry_only_after_infrastructure_failure(tmp_path: Path) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    a = store.plan_attempt(eid)
    store.dispatch(a.attempt_id, REQ)
    store.record_outcome(a.attempt_id, "response")
    with pytest.raises(LedgerError, match="retry only after"):
        store.plan_attempt(eid)


def test_torn_final_line_is_recovered_explicitly(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.plan_episode(_spec())
    path = tmp_path / "run" / "journal.jsonl"
    with path.open("ab") as fh:
        fh.write(b'{"seq":1,"prev":"sha2')  # crash mid-write
    reopened = AttemptLedgerStore(tmp_path / "run")
    assert reopened.journal.recovered_bytes > 0
    assert reopened.journal.events[-1].kind == "journal_recovered"
    assert reopened.ledger.recoveries == 1


def test_corruption_in_the_middle_fails_visibly(tmp_path: Path) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    store.plan_attempt(eid)
    path = tmp_path / "run" / "journal.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(lines[0].replace(b'"repetition":0', b'"repetition":9') + lines[1])
    with pytest.raises(StorageError):
        AttemptLedgerStore(tmp_path / "run")


def test_index_is_rebuildable_from_the_journal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for rep in range(3):
        eid = store.plan_episode(_spec(rep))
        a = store.plan_attempt(eid)
        store.dispatch(a.attempt_id, REQ)
        store.record_outcome(a.attempt_id, "terminal_error", error_class="sandbox_start")
    db = tmp_path / "index.sqlite"
    assert rebuild_index(tmp_path / "run" / "journal.jsonl", db) == {"episodes": 3, "attempts": 3}
    first = sqlite3.connect(db).execute("SELECT * FROM attempts ORDER BY attempt_id").fetchall()
    db.unlink()
    rebuild_index(tmp_path / "run" / "journal.jsonl", db)
    assert (
        sqlite3.connect(db).execute("SELECT * FROM attempts ORDER BY attempt_id").fetchall()
        == first
    )


def test_the_run_journal_seals_into_a_valid_bundle(tmp_path: Path) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    a = store.plan_attempt(eid)
    store.dispatch(a.attempt_id, REQ)
    store.record_outcome(a.attempt_id, "response")
    store.finalize(eid, Disposition.COMPLETED_NO_FINDINGS, attempt_id=a.attempt_id)
    files = build_bundle(
        [
            Member("verdicts.json", canonical_json([]), "verdicts"),
            Member("metrics.json", canonical_json({}), "metrics"),
        ],
        store.journal.events,
        blobs=[],
        versions={"matcher": "0.1.0"},
        generator={"name": "aureproof", "version": "test"},
    )
    assert files["journal.jsonl"] == store.journal.raw()  # byte-identical journal
    assert validate(files).valid


@settings(max_examples=40, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.sampled_from(["work", "crash"]),
            st.sampled_from(["response", "terminal_error", "unknown"]),
        ),
        min_size=1,
        max_size=12,
    )
)
def test_any_crash_sequence_keeps_every_invariant(
    tmp_path_factory: pytest.TempPathFactory, steps: list[tuple[str, str]]
) -> None:
    root = tmp_path_factory.mktemp("prop")
    store = AttemptLedgerStore(root, clock=_clock())  # type: ignore[arg-type]
    eid = store.plan_episode(_spec())
    for action, outcome in steps:
        episode = store.ledger.episodes[eid]
        if episode.final is not None:
            break
        if action == "crash":
            store = AttemptLedgerStore(root, clock=_clock())  # type: ignore[arg-type]
            store.recover()
            continue
        last = episode.attempts[-1].outcome if episode.attempts else None
        if last is not None and last.outcome == "response":
            store.finalize(
                eid, Disposition.COMPLETED_NO_FINDINGS, attempt_id=episode.attempts[-1].attempt_id
            )
            continue
        attempt = store.plan_attempt(eid)
        store.dispatch(attempt.attempt_id, REQ)
        store.record_outcome(
            attempt.attempt_id,
            outcome,  # type: ignore[arg-type]
            error_class=None if outcome == "response" else "infra",
        )
    final = AttemptLedgerStore(root)
    final.recover()
    episode = final.ledger.episodes[eid]
    ids = [a.attempt_id for a in episode.attempts]
    assert ids == [f"{eid}/a{i}" for i in range(len(ids))]  # consecutive, unique, kept
    assert all(a.outcome is not None for a in episode.attempts)  # nothing left in doubt
    assert sum(e.kind == "episode_finalized" for e in final.journal.events) <= 1


def test_closing_a_run_gives_every_episode_exactly_one_disposition(tmp_path: Path) -> None:
    store = _store(tmp_path)
    done, stuck, never = (store.plan_episode(_spec(r)) for r in range(3))
    a = store.plan_attempt(done)
    store.dispatch(a.attempt_id, REQ)
    store.record_outcome(a.attempt_id, "response")
    store.finalize(done, Disposition.COMPLETED_NO_FINDINGS, attempt_id=a.attempt_id)
    b = store.plan_attempt(stuck)
    store.dispatch(b.attempt_id, REQ)  # crash before the outcome
    assert sorted(store.close_run("operator stopped the run")) == sorted([stuck, never])
    finals = {eid: e.final for eid, e in store.ledger.episodes.items()}
    assert all(f is not None for f in finals.values())
    assert finals[stuck].disposition is Disposition.INFRA_FAILURE  # type: ignore[union-attr]
    assert "operator stopped the run" in (finals[never].reason or "")  # type: ignore[union-attr]
    assert store.close_run("again") == []  # idempotent
    kinds = [e.kind for e in store.journal.events]
    assert kinds.count("episode_finalized") == 3


def _tool(store: AttemptLedgerStore, attempt_id: str, source: ObservationSource) -> None:
    store.record_tool(
        attempt_id,
        tool="bash",
        input_sha256="a" * 64,
        output_sha256="b" * 64 if source == ObservationSource.CONTROLLER_OBSERVED else None,
        error=None,
        source=source,
    )


def test_tool_events_sit_between_dispatch_and_outcome_with_their_trust_tier(
    tmp_path: Path,
) -> None:
    """Issue #43: tool calls are journaled per attempt, tagged by who observed them."""
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    a = store.plan_attempt(eid)
    with pytest.raises(LedgerError):  # not dispatched yet
        _tool(store, a.attempt_id, ObservationSource.CONTROLLER_OBSERVED)
    store.dispatch(a.attempt_id, REQ)
    _tool(store, a.attempt_id, ObservationSource.CONTROLLER_OBSERVED)
    _tool(store, a.attempt_id, ObservationSource.AGENT_REPORTED)
    with pytest.raises(LedgerError):  # imported data is never a tool observation
        _tool(store, a.attempt_id, ObservationSource.IMPORTED)
    store.record_outcome(a.attempt_id, "response")
    with pytest.raises(LedgerError):  # the attempt is closed
        _tool(store, a.attempt_id, ObservationSource.CONTROLLER_OBSERVED)
    sources = [e.observation_source for e in store.journal.events if e.kind == "tool_observed"]
    assert sources == ["controller_observed", "agent_reported"]
    assert AttemptLedgerStore(tmp_path / "run").ledger.episodes[eid].attempts[0].tool_events == 2


def test_only_tool_events_may_be_agent_reported(tmp_path: Path) -> None:
    store = _store(tmp_path)
    eid = store.plan_episode(_spec())
    a = store.plan_attempt(eid)
    event = store.journal.events[-1].model_copy(
        update={"seq": len(store.journal.events), "observation_source": "agent_reported"}
    )
    with pytest.raises(LedgerError, match="attempt_planned cannot be agent_reported"):
        copy.deepcopy(store.ledger).apply(event)
    assert a.attempt_id.endswith("/a0")
